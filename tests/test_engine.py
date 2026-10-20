"""End-to-end engine check on a synthetic song with a real tempo change (128 -> 104 BPM).

usage: python tests/test_engine.py <engine command...>
e.g.   python tests/test_engine.py python engine/click_engine.py
       python tests/test_engine.py "dist/Click Studio/click_engine.exe"
"""
import json, os, subprocess, sys, tempfile

import numpy as np
import soundfile as sf

SR = 44100
ENGINE = sys.argv[1:] or [sys.executable, os.path.join(os.path.dirname(__file__), "..", "engine", "click_engine.py")]


def beat_times():
    """Beats: 40 s at 128 BPM, a 10 s ritardando to 104 BPM, then 30 s at 104 BPM; first beat at 0.30 s."""
    t, out = 0.30, []
    while t < 80:
        out.append(t)
        bpm = 128 if t < 40 else (104 if t > 50 else 128 - 24 * (t - 40) / 10)
        t += 60 / bpm
    return np.array(out)


def synth(beats):
    n = int(SR * (beats[-1] + 1.5))
    x = np.zeros(n, np.float32)
    rng = np.random.default_rng(1)

    def put(at, s, g=1.0):
        i = int(at * SR)
        e = min(n, i + len(s))
        x[i:e] += g * s[: e - i]
    u = np.arange(int(0.25 * SR)) / SR
    kick = np.sin(2 * np.pi * (50 + 80 * np.exp(-u * 30)) * u) * np.exp(-u * 12)
    snare = rng.uniform(-1, 1, u.size) * np.exp(-u * 25) * 0.6
    hat = rng.uniform(-1, 1, int(0.04 * SR)) * np.exp(-np.arange(int(0.04 * SR)) / SR * 120) * 0.25
    for i, b in enumerate(beats):
        bar_pos = i % 4
        put(b, kick if bar_pos in (0, 2) else snare)
        nxt = beats[i + 1] if i + 1 < len(beats) else b + (b - beats[i - 1])
        put(b, hat)
        put((b + nxt) / 2, hat, 0.6)
        f = [55, 55, 73.4, 65.4][(i // 4) % 4]  # bass changes every bar: helps the downbeat network
        if bar_pos == 0:
            v = np.arange(int((nxt - b) * 4 * SR * 0.9)) / SR
            put(b, (np.sin(2 * np.pi * f * v) * np.exp(-v * 1.5) * 0.35).astype(np.float32))
    x /= np.abs(x).max() / 0.9
    return np.stack([x, x], 1)


def run(args):
    r = subprocess.run(ENGINE + args, capture_output=True, text=True, encoding="utf-8")
    lines = [json.loads(l) for l in r.stdout.splitlines() if l.startswith("{")]
    done = [l for l in lines if l.get("event") in ("done", "ok")]
    assert r.returncode == 0 and done, f"engine failed ({r.returncode}): {r.stdout[-2000:]} {r.stderr[-2000:]}"
    return done[-1]


def onsets(path):
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    y = np.abs(y[:, 0])
    out, last = [], -10 ** 9
    for k in np.flatnonzero(y > 0.05):
        if k - last > int(0.1 * sr):
            out.append(k / sr)
        last = k
    return np.array(out)


def main():
    assert run(["--check"])["event"] == "ok"
    beats = beat_times()
    with tempfile.TemporaryDirectory() as d:
        song = os.path.join(d, "synth song.wav")
        sf.write(song, synth(beats), SR, subtype="PCM_16")
        cache = os.path.join(d, "cache")
        common = ["--input", song, "--output-dir", d, "--meter", "4/4", "--count-in", "0", "--cache-dir", cache]
        r = run(common + ["--name", "synth_click", "--format", "wav"])
        print("wav:", r)
        assert 125 <= r["bpm_max"] <= 131 and 101 <= r["bpm_min"] <= 107, "tempo change not followed"
        got = onsets(os.path.join(d, "synth_click.wav"))
        err = np.array([np.min(np.abs(got - b)) for b in beats[4:-4]])
        print(f"clicks {len(got)} / beats {len(beats)}, median error {1000 * np.median(err):.1f} ms, max {1000 * err.max():.1f} ms")
        assert abs(len(got) - len(beats)) <= 2, "missing or extra clicks"
        assert np.median(err) < 0.02 and np.percentile(err, 95) < 0.04, "clicks off the beat"

        r = run(common + ["--name", "synth_lr", "--format", "mp3", "--layout", "LR", "--tail-bars", "2"])
        assert os.path.getsize(os.path.join(d, "synth_lr.mp3")) > 10000
        y, _ = sf.read(os.path.join(d, "synth_lr.mp3"), always_2d=True)
        assert y.shape[1] == 2
        r = run(common + ["--name", "synth_midi", "--format", "midi"])
        assert open(os.path.join(d, "synth_midi.mid"), "rb").read(4) == b"MThd"
        r = run(["--input", song, "--preview-dir", os.path.join(d, "pv"), "--cache-dir", cache, "--count-in", "2"])
        assert r["offset"] > 0 and os.path.exists(os.path.join(d, "pv", "click.wav"))
        r = run(["--demo", os.path.join(d, "demo.wav"), "--sound", "cowbell"])
        if sys.platform == "win32":  # M4A/AAC through the bundled FFmpeg libraries
            import av
            m4a = os.path.join(d, "song.m4a")
            with av.open(m4a, "w") as out:
                st = out.add_stream("aac", rate=SR, layout="stereo")
                pcm = synth(beats)[: SR * 30].T.copy()
                for i in range(0, pcm.shape[1], 1024):
                    fr = av.AudioFrame.from_ndarray(np.ascontiguousarray(pcm[:, i:i + 1024].reshape(1, -1)), format="flt",
                                                    layout="stereo")
                    fr.sample_rate = SR
                    for p in st.encode(fr):
                        out.mux(p)
                for p in st.encode(None):
                    out.mux(p)
            r = run(["--input", m4a, "--output-dir", d, "--name", "m4a_click", "--meter", "4/4", "--count-in", "0"])
            assert 125 <= r["bpm"] <= 131, r
    print("engine tests passed")


if __name__ == "__main__":
    main()
