#!/usr/bin/env python3
"""Click Studio engine: tracks beats/downbeats of a song (madmom) and renders a click track.

Prints one JSON object per line on stdout:
  {"event": "progress", "stage": "...", "value": 0..1}
  {"event": "done", "files": [...], ...}
  {"event": "error", "message": "..."}
"""
import argparse, hashlib, json, math, os, shutil, struct, subprocess, sys, tempfile

SR = 44100
NOTE_NAMES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
# meter -> (beats per bar used for tracking, quarter notes per tracked beat, MIDI time-signature numerator/denominator)
METERS = {
    "2/4": ([2], 1.0, (2, 4)), "3/4": ([3], 1.0, (3, 4)), "4/4": ([4], 1.0, (4, 4)),
    "5/4": ([5], 1.0, (5, 4)), "6/8": ([2], 1.5, (6, 8)), "12/8": ([4], 1.5, (12, 8)),
}


LANG = "ru"


def L(ru, en):
    return ru if LANG == "ru" else en


def emit(event, **kw):
    print(json.dumps({"event": event, **kw}, ensure_ascii=False), flush=True)


def progress(stage, value):
    emit("progress", stage=stage, value=round(value, 3))


def note_to_midi(name):
    name = name.strip().upper()
    pitch = name.rstrip("-0123456789")
    return 12 * (int(name[len(pitch):]) + 1) + NOTE_NAMES[pitch]


def midi_to_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def find_ffmpeg(hint):
    for p in [hint, shutil.which("ffmpeg"), "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"]:
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def decode_av(path):
    """Windows: PyAV (FFmpeg libraries bundled with the app) decodes M4A/AAC/ALAC/WMA/OPUS and video."""
    import av
    import numpy as np
    chunks, sr = [], None
    with av.open(path) as f:
        stream = f.streams.audio[0]
        res = av.AudioResampler(format="flt", layout="stereo")
        for frame in f.decode(stream):
            sr = sr or frame.sample_rate
            for fr in res.resample(frame):
                chunks.append(fr.to_ndarray().reshape(-1, 2))
        for fr in res.resample(None):
            chunks.append(fr.to_ndarray().reshape(-1, 2))
    if not chunks:
        raise RuntimeError("no audio")
    return np.concatenate(chunks).astype(np.float32), sr


def load_audio(path, ff_hint, tmp):
    """Stereo float32 at SR. libsndfile reads MP3/WAV/FLAC/OGG/AIFF; macOS afconvert (Windows: bundled PyAV)
    covers M4A/AAC/ALAC; ffmpeg (if the user has it) is only a last resort for video and rare formats."""
    import numpy as np
    import soundfile as sf
    try:
        x, sr = sf.read(path, dtype="float32", always_2d=True)
    except Exception:
        x = None
        if sys.platform == "win32":
            try:
                x, sr = decode_av(path)
            except Exception:
                x = None
    if x is None:
        w = os.path.join(tmp, "decoded.wav")
        r = subprocess.run(["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEF32", path, w],
                           capture_output=True) if sys.platform == "darwin" else None
        if r is None or r.returncode:
            ff = find_ffmpeg(ff_hint)
            if not ff:
                raise RuntimeError(L("Не удалось прочитать файл: такой формат не поддерживается",
                                     "Can't read this file: the format is not supported"))
            r = subprocess.run([ff, "-v", "error", "-y", "-i", path, "-vn", "-c:a", "pcm_f32le", w], capture_output=True)
            if r.returncode:
                raise RuntimeError(L("Не удалось прочитать файл", "Can't read the file"))
        x, sr = sf.read(w, dtype="float32", always_2d=True)
    x = np.repeat(x, 2, 1) if x.shape[1] == 1 else x[:, :2]
    if sr != SR:
        from scipy.signal import resample_poly
        g = math.gcd(int(sr), SR)
        x = resample_poly(x, SR // g, int(sr) // g, axis=0).astype(np.float32)
    return np.ascontiguousarray(x)


def write_audio(path, x, fmt, bitrate):
    import soundfile as sf
    if fmt == "mp3":  # libsndfile CBR: compression 0.0 = 320, 0.2 = 256, 0.4 = 192 kbps
        sf.write(path, x, SR, format="MP3", bitrate_mode="CONSTANT", compression_level={320: 0.0, 256: 0.2}.get(bitrate, 0.4))
    else:
        sf.write(path, x, SR, subtype="PCM_24")


def repair(act, A, bpb, a):
    """The flexible pass follows live tempo but can slip on weak passages (synth pads, breaks): it inserts or
    drops a beat, which sounds like a sudden rush and shifts "one". Such spots, and beats it missed at the very
    start or end, are taken from a stiffer pass over the same network output. Gradual tempo changes stay as they are."""
    import numpy as np
    from scipy.ndimage import median_filter
    from madmom.features.downbeats import DBNDownBeatTrackingProcessor
    d = np.diff(A[:, 0])
    md = float(np.median(d))
    B = DBNDownBeatTrackingProcessor(beats_per_bar=bpb, fps=100, min_bpm=a.min_bpm, max_bpm=a.max_bpm,
                                     transition_lambda=1000)(act)
    if len(B) < 8 or abs(float(np.median(np.diff(B[:, 0]))) / md - 1) > 0.03:
        return A  # the stiff pass locked to another tempo (half/double): keep the flexible one
    bad = np.flatnonzero(np.abs(d / median_filter(d, 17, mode="nearest") - 1) > 0.15)  # live rubato stays under ~10%
    # a slip usually means the flexible pass rode the off-beats (synth stabs) before or after it:
    # widen each slip over the neighbouring beats where the two passes disagree
    k = np.clip(np.searchsorted(B[:, 0], A[:, 0]), 1, len(B) - 1)
    matched = np.minimum(np.abs(B[k - 1, 0] - A[:, 0]), np.abs(B[k, 0] - A[:, 0])) < 0.07
    keep_a = np.ones(len(A), bool)
    take_b = np.zeros(len(B), bool)
    if matched[0]:
        take_b |= B[:, 0] < A[0, 0] - 0.25 * md  # beats missed at the very start
    if matched[-1]:
        take_b |= B[:, 0] > A[-1, 0] + 0.25 * md
    for i in bad:
        lo, hi = max(0, i - 2), min(len(A) - 1, i + 3)
        while lo > 0 and not matched[lo - 1]:
            lo -= 1
        while hi < len(A) - 1 and not matched[hi + 1]:
            hi += 1
        s = -np.inf if lo == 0 else A[lo, 0]
        e = np.inf if hi == len(A) - 1 else A[hi, 0]
        keep_a &= ~((A[:, 0] >= s) & (A[:, 0] <= e))
        take_b |= (B[:, 0] >= s) & (B[:, 0] <= e)
    if keep_a.all() and not take_b.any():
        return A
    R = np.concatenate([A[keep_a], B[take_b]])
    R = R[np.argsort(R[:, 0])]
    R = R[np.r_[True, np.diff(R[:, 0]) > 0.5 * md]]
    j = np.clip(np.searchsorted(B[:, 0], R[:, 0]), 1, len(B) - 1)
    j = np.where(np.abs(B[j - 1, 0] - R[:, 0]) < np.abs(B[j, 0] - R[:, 0]), j - 1, j)
    near = np.abs(B[j, 0] - R[:, 0]) < 0.07
    R[near, 1] = B[j[near], 1]  # bar numbering from the steadier pass, where the beats coincide
    return R


def track(a, song, bpb, tmp):
    """madmom beats+downbeats, cached per file and tracking settings (re-renders and previews are instant)."""
    import numpy as np
    import soundfile as sf
    key = json.dumps(["v2", os.path.abspath(a.input), os.path.getsize(a.input), os.path.getmtime(a.input), bpb, a.min_bpm, a.max_bpm])
    cache = os.path.join(a.cache_dir, hashlib.sha1(key.encode()).hexdigest() + ".npy") if a.cache_dir else None
    if cache and os.path.exists(cache):
        return np.load(cache)
    progress("analyze", 0.15)
    mono_wav = os.path.join(tmp, "mono.wav")
    sf.write(mono_wav, song.mean(1), SR, subtype="PCM_16")
    from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor
    act = RNNDownBeatProcessor()(mono_wav)
    progress("track", 0.6)
    r = DBNDownBeatTrackingProcessor(beats_per_bar=bpb, fps=100, min_bpm=a.min_bpm, max_bpm=a.max_bpm)(act)
    if len(r) >= 8:
        r = repair(act, r, bpb, a)
    if cache:
        os.makedirs(a.cache_dir, exist_ok=True)
        np.save(cache, r)
    return r


# ---------------------------------------------------------------- sounds
def make_sound(kind, freq, amp):
    import numpy as np
    rng = np.random.default_rng(int(freq))
    def t(sec): return np.arange(int(SR * sec)) / SR
    if kind == "wood":
        u = t(0.06)
        s = np.sin(2 * np.pi * freq * u) * np.exp(-u * 90) + 0.5 * np.sin(2 * np.pi * freq * 2.76 * u) * np.exp(-u * 160)
        s[:60] += rng.uniform(-1, 1, 60) * np.linspace(0.6, 0, 60)
    elif kind == "cowbell":
        u = t(0.18)
        sq = lambda f: np.sign(np.sin(2 * np.pi * f * u))
        s = (sq(freq * 0.5) + sq(freq * 0.5 * 1.48)) * 0.5
        s = np.convolve(s, [0.25, 0.5, 0.25], "same") * (0.7 * np.exp(-u * 40) + 0.3 * np.exp(-u * 12))
    elif kind == "rim":
        u = t(0.05)
        noise = rng.uniform(-1, 1, u.size)
        noise = np.diff(noise, prepend=0) * np.exp(-u * 300)
        s = 0.6 * noise + np.sin(2 * np.pi * freq * 0.6 * u) * np.exp(-u * 120)
    elif kind == "hat":
        u = t(0.05)
        noise = rng.uniform(-1, 1, u.size)
        bright = min(1.0, freq / 2000)
        noise = noise - bright * np.convolve(noise, np.ones(4) / 4, "same")
        s = noise * np.exp(-u * 110)
    elif kind == "digital":
        u = t(0.025)
        s = np.sign(np.sin(2 * np.pi * freq * u)) * 0.6 * np.exp(-u * 60)
    else:  # classic
        u = t(0.03)
        s = np.sin(2 * np.pi * freq * u) * np.exp(-u * 150)
    s[: min(32, s.size)] *= np.linspace(0, 1, min(32, s.size))  # no DC click at onset
    return amp * s / max(1e-9, np.abs(s).max())


# ---------------------------------------------------------------- MIDI
def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def write_midi(path, hits, beat_times, beat_ticks, timesig, channel):
    """hits: list of (beat_index_float, note, velocity); beat_times: absolute seconds of each integer beat index."""
    PPQ = 480
    ev = []  # (tick, order, bytes)
    num, den = timesig
    ev.append((0, 0, b"\xff\x58\x04" + bytes([num, {4: 2, 8: 3}[den], 24, 8])))
    ev.append((0, 0, b"\xff\x03" + vlq(11) + b"Click Track"))
    lead = beat_times[0]
    tick0 = 0
    if lead > 0.001:  # silence before the first click, at the opening tempo
        step = beat_times[1] - beat_times[0]
        tick0 = max(1, round(lead / step * beat_ticks))
        ev.append((0, 0, b"\xff\x51\x03" + struct.pack(">I", round(lead * 1e6 * PPQ / tick0))[1:]))
    for i in range(len(beat_times) - 1):
        dt = beat_times[i + 1] - beat_times[i]
        ev.append((tick0 + i * beat_ticks, 0, b"\xff\x51\x03" + struct.pack(">I", round(dt * 1e6 * PPQ / beat_ticks))[1:]))
    ch = channel - 1
    for pos, note, vel in hits:
        tk = tick0 + round(pos * beat_ticks)
        ev.append((tk, 2, bytes([0x90 | ch, note, vel])))
        ev.append((tk + PPQ // 8, 1, bytes([0x80 | ch, note, 0])))
    ev.sort(key=lambda e: (e[0], e[1]))
    data, last = b"", 0
    for tk, _, b in ev:
        data += vlq(tk - last) + b
        last = tk
    data += b"\x00\xff\x2f\x00"
    with open(path, "wb") as f:
        f.write(b"MThd" + struct.pack(">IHHH", 6, 0, 1, PPQ) + b"MTrk" + struct.pack(">I", len(data)) + data)


# ---------------------------------------------------------------- main
def run(a):
    import numpy as np
    import soundfile as sf
    from scipy.signal import savgol_filter

    tmp = tempfile.mkdtemp(prefix="clickstudio-")
    try:
        progress("decode", 0.05)
        song = load_audio(a.input, a.ffmpeg, tmp)
        dur = len(song) / SR
        bpb, beat_q, timesig = METERS.get(a.meter, ([3, 4], 1.0, None))
        r = track(a, song, bpb, tmp)
        if len(r) < 8:
            raise RuntimeError(L("Не удалось найти ритм: слишком мало долей", "Could not find the beat: too few beats"))
        t, pos = r[:, 0], r[:, 1].astype(int)
        if len(t) >= 9:
            sm = savgol_filter(t, 7, 2)  # remove ~10 ms tracker jitter, keep tempo changes
            if np.all(np.diff(sm) > 0):
                t = sm
        beats_per_bar = int(pos.max())
        if a.downbeat_shift:  # user correction when the tracker picked the wrong "one"
            pos = (pos - 1 - a.downbeat_shift) % beats_per_bar + 1
        t = t + a.nudge_ms / 1000.0
        if timesig is None:
            timesig = (beats_per_bar, 4)
        # drop beats before the first downbeat? keep them as a pickup, bar numbering from first downbeat
        T0 = float(np.median(np.diff(t[: min(9, len(t))])))

        progress("render", 0.75)
        # count-in: whole bars at the opening tempo, ending one beat before the first downbeat
        first_down = int(np.argmax(pos == 1))
        cin = a.count_in * beats_per_bar
        start = t[first_down] - cin * T0
        pickup = t[:first_down]
        pad = max(0.0, -start) if cin else max(0.0, -t[0])
        cin_times = [start + k * T0 + pad for k in range(cin)]
        cin_pos = [k % beats_per_bar + 1 for k in range(cin)]
        beat_times = list(cin_times) + [x + pad for x in t]
        beat_pos = cin_pos + list(pos)
        if cin and first_down:  # pickup beats overlap the count-in; drop the count-in beats they cover
            keep = [i for i in range(cin) if cin_times[i] < pickup[0] + pad - T0 / 2]
            beat_times = [cin_times[i] for i in keep] + [x + pad for x in t]
            beat_pos = [cin_pos[i] for i in keep] + list(pos)

        if a.tail_bars:  # finish the last bar, then whole bars at the closing tempo
            T1 = float(np.median(np.diff(t[-min(9, len(t)):])))
            last, p = beat_times[-1], beat_pos[-1]
            for k in range(1, beats_per_bar - p + a.tail_bars * beats_per_bar + 1):
                beat_times.append(last + k * T1)
                beat_pos.append((p + k - 1) % beats_per_bar + 1)

        acc_n, beat_n = note_to_midi(a.accent_note), note_to_midi(a.beat_note)
        sub = max(1, a.subdivision)
        hits = []  # (beat index float, kind) kind: 0 accent, 1 beat, 2 sub
        for i, p in enumerate(beat_pos):
            hits.append((float(i), 0 if (p == 1 and a.accent) else 1))
            if i + 1 < len(beat_times):
                for k in range(1, sub):
                    hits.append((i + k / sub, 2))
        if sub > 1 and len(beat_times) > 1:  # subdivisions after the last beat
            last = beat_times[-1] - beat_times[-2]
            for k in range(1, sub):
                if beat_times[-1] + last * k / sub < pad + dur:
                    hits.append((len(beat_times) - 1 + k / sub, 2))

        def time_of(x):
            i = int(x)
            if i + 1 < len(beat_times):
                return beat_times[i] + (beat_times[i + 1] - beat_times[i]) * (x - i)
            return beat_times[-1] + (beat_times[-1] - beat_times[-2]) * (x - i)

        files = []
        end = max(pad + dur, beat_times[-1] + 0.6)
        if a.format in ("wav", "mp3") or a.preview or a.preview_dir:
            n = int(round(end * SR)) + SR // 4
            click = np.zeros(n, dtype=np.float32)
            sounds = [make_sound(a.sound, midi_to_hz(acc_n), 0.95), make_sound(a.sound, midi_to_hz(beat_n), 0.7),
                      make_sound(a.sound, midi_to_hz(beat_n), 0.35)]
            for x, kind in hits:
                s = int(round(time_of(x) * SR))
                b = sounds[kind]
                if 0 <= s < n:
                    e = min(n, s + b.size)
                    click[s:e] += b[: e - s]
            click *= a.volume
            peak = np.abs(click).max()
            if peak > 0.99:
                click *= 0.99 / peak
            song_p = np.zeros((n, 2), np.float32)  # the song shifted by the count-in, same length as the click
            s0 = int(round(pad * SR))
            m = min(len(song), n - s0)
            song_p[s0:s0 + m] = song[:m]

        if a.preview_dir:  # mono stems for the app's player; volumes and channels are applied live there
            os.makedirs(a.preview_dir, exist_ok=True)
            for nm, x in (("click.wav", click), ("song.wav", song_p.mean(1))):
                sf.write(os.path.join(a.preview_dir, nm), x, SR, subtype="FLOAT")
                files.append(os.path.join(a.preview_dir, nm))
        else:
            os.makedirs(a.output_dir, exist_ok=True)
            stem = os.path.join(a.output_dir, a.name)
            if a.format == "midi":
                notes, vels = [acc_n, beat_n, beat_n], [120, 90, 55]
                write_midi(stem + ".mid", [(x, notes[k], vels[k]) for x, k in hits], beat_times,
                           round(480 * beat_q), timesig, a.midi_channel)
                files.append(stem + ".mid")
            else:
                if a.layout == "click":
                    out = click
                else:  # click in one channel, the song (mono) in the other
                    sm = song_p.mean(1) * a.song_volume
                    out = np.stack([click, sm] if a.layout == "LR" else [sm, click], 1)
                    out /= max(1.0, float(np.abs(out).max()) / 0.99)
                write_audio(f"{stem}.{a.format}", out, a.format, a.bitrate)
                files.append(f"{stem}.{a.format}")
            if a.preview:
                progress("preview", 0.9)
                mix = song_p * 0.8 + click[:, None] * 0.6
                mix /= max(1.0, float(np.abs(mix).max()))
                out = stem + L(" (проверка).mp3", " (check).mp3")
                write_audio(out, mix, "mp3", 256)
                files.append(out)

        bpm = 60 / np.diff(t)
        emit("done", files=files, meter=f"{timesig[0]}/{timesig[1]}", bpm=round(float(np.median(bpm)) / beat_q, 1),
             bpm_min=round(float(np.percentile(bpm, 5)) / beat_q, 1), bpm_max=round(float(np.percentile(bpm, 95)) / beat_q, 1),
             offset=round(pad, 3), clicks=len(hits), duration=round(dur, 2))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_demo(a):
    """Two bars at 120 BPM with the chosen sound, for previewing in the app (no analysis)."""
    import numpy as np
    import soundfile as sf
    bpb, beat_q, _ = METERS.get(a.meter, ([4], 1.0, None))
    n_beats, step, sub = bpb[0] * 2, 0.5 * beat_q, max(1, a.subdivision)
    acc, beat = make_sound(a.sound, midi_to_hz(note_to_midi(a.accent_note)), 0.95), make_sound(a.sound, midi_to_hz(note_to_midi(a.beat_note)), 0.7)
    weak = make_sound(a.sound, midi_to_hz(note_to_midi(a.beat_note)), 0.35)
    out = np.zeros(int(SR * (n_beats * step + 0.3)), np.float32)
    for i in range(n_beats):
        for k in range(sub):
            b = (acc if (i % bpb[0] == 0 and a.accent) else beat) if k == 0 else weak
            s = int(SR * (0.05 + i * step + k * step / sub))
            out[s:s + b.size] += b[: out.size - s]
    sf.write(a.demo, out * a.volume, SR)
    emit("ok", file=a.demo)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input")
    p.add_argument("--output-dir")
    p.add_argument("--name")
    p.add_argument("--demo", help="render a short preview of the click sound to this .wav")
    p.add_argument("--format", choices=["wav", "mp3", "midi"], default="wav")
    p.add_argument("--meter", default="auto")
    p.add_argument("--subdivision", type=int, default=1)
    p.add_argument("--sound", default="classic")
    p.add_argument("--accent-note", default="G6")
    p.add_argument("--beat-note", default="C6")
    p.add_argument("--accent", type=int, default=1)
    p.add_argument("--count-in", type=int, default=1)
    p.add_argument("--volume", type=float, default=1.0)
    p.add_argument("--bitrate", type=int, default=320)
    p.add_argument("--midi-channel", type=int, default=10)
    p.add_argument("--min-bpm", type=float, default=55)
    p.add_argument("--max-bpm", type=float, default=215)
    p.add_argument("--downbeat-shift", type=int, default=0)
    p.add_argument("--nudge-ms", type=float, default=0)
    p.add_argument("--preview", type=int, default=0)
    p.add_argument("--tail-bars", type=int, default=0)
    p.add_argument("--layout", choices=["click", "LR", "RL"], default="click")
    p.add_argument("--song-volume", type=float, default=1.0)
    p.add_argument("--preview-dir", default="", help="write mono click.wav and song.wav here instead of the output")
    p.add_argument("--cache-dir", default="")
    p.add_argument("--lang", choices=["ru", "en"], default="ru")
    p.add_argument("--ffmpeg", default="")
    p.add_argument("--check", action="store_true", help="only verify dependencies")
    try:
        if "--check" in sys.argv:
            import numpy, scipy, soundfile, madmom  # noqa: F401
            emit("ok")
            return
        a = p.parse_args()
        global LANG
        LANG = a.lang
        if a.demo:
            run_demo(a)
        elif not (a.input and (a.preview_dir or (a.output_dir and a.name))):
            raise RuntimeError("--input and --output-dir/--name or --preview-dir are required")
        else:
            run(a)
    except Exception as e:  # report to the app instead of a traceback
        emit("error", message=str(e) or e.__class__.__name__)
        sys.exit(1)


if __name__ == "__main__":
    main()
