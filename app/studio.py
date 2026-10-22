"""Click Studio for Windows: settings, the render queue and the player (port of the Mac app's Models/Engine)."""
import json, os, shutil, subprocess, sys, tempfile, uuid
from dataclasses import asdict, dataclass, field, fields

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

import license as lic

LANG = ["ru"]


def L(ru, en):
    return en if LANG[0] == "en" else ru


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(m):
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"


FORMATS = ["wav", "mp3", "midi"]
METERS = ["auto", "2/4", "3/4", "4/4", "5/4", "6/8", "12/8"]
SUBDIVISIONS = [1, 2, 3, 4]
SOUNDS = ["classic", "wood", "cowbell", "rim", "hat", "digital"]
LAYOUTS = ["click", "LR", "RL"]
AUDIO_EXT = {"mp3", "wav", "aif", "aiff", "aifc", "flac", "m4a", "aac", "alac", "ogg", "oga", "opus", "wma", "caf",
             "mp4", "mov", "m4v", "mkv", "webm", "ape", "wv"}


def format_caption(f):
    return {"wav": L("Без потерь, 24 бит", "Lossless, 24-bit"), "mp3": L("Компактный файл", "Compact file"),
            "midi": L("Темп-карта для DAW", "Tempo map for DAW")}[f]


def meter_title(m):
    return L("Авто", "Auto") if m == "auto" else m


def sub_title(d):
    return {1: L("Четверти", "Quarters"), 2: L("Восьмые", "Eighths"), 3: L("Триоли", "Triplets"),
            4: L("Шестнадц.", "16ths")}[d]


SUB_GLYPH = {1: "♩", 2: "♫", 3: "³♪", 4: "♬"}


def sound_title(s):
    return {"classic": L("Классика", "Classic"), "wood": L("Вуд-блок", "Wood block"), "cowbell": L("Ковбелл", "Cowbell"),
            "rim": L("Римшот", "Rimshot"), "hat": L("Хай-хэт", "Hi-hat"), "digital": L("Цифровой", "Digital")}[s]


SOUND_GLYPH = {"classic": "♩", "wood": "▤", "cowbell": "◭", "rim": "◎", "hat": "≋", "digital": "⌁"}


def layout_title(o):
    return {"click": L("Только клик", "Click only"), "LR": L("Клик L · песня R", "Click L · song R"),
            "RL": L("Песня L · клик R", "Song L · click R")}[o]


def layout_caption(o):
    return {"click": L("Клик отдельным файлом", "Click as a separate file"),
            "LR": L("Клик в левом канале, песня в правом", "Click in the left channel, song in the right"),
            "RL": L("Песня в левом канале, клик в правом", "Song in the left channel, click in the right")}[o]


LAYOUT_SUFFIX = {"click": "_click", "LR": "_click-L", "RL": "_click-R"}


def note_presets():
    return [(L("Классика", "Classic") + "  G6 / C6", 91, 84), (L("GM вуд-блок", "GM wood block") + "  76 / 77", 76, 77),
            (L("GM метроном", "GM metronome") + "  34 / 33", 34, 33), (L("GM сайд-стик", "GM side stick") + "  37 / 37", 37, 37),
            (L("GM ковбелл", "GM cowbell") + "  56 / 56", 56, 56)]


def local_dir(*parts):
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.cache")
    d = os.path.join(base, "Click Studio", *parts)
    os.makedirs(d, exist_ok=True)
    return d


@dataclass
class Settings:
    format: str = "wav"
    mp3Bitrate: int = 320
    midiChannel: int = 10
    meter: str = "auto"
    subdivision: int = 1
    sound: str = "classic"
    accentNote: int = 91
    beatNote: int = 84
    accentDownbeat: bool = True
    countInBars: int = 1
    tailBars: int = 0
    layout: str = "click"
    volume: float = 0.9
    songVolume: float = 0.8
    downbeatShift: int = 0
    nudgeMs: float = 0.0
    minBPM: float = 55.0
    maxBPM: float = 215.0
    makePreview: bool = False
    outputFolder: str = ""
    language: str = field(default_factory=lambda: "ru")

    @staticmethod
    def path():
        return os.path.join(lic.data_dir(), "settings.json")

    @classmethod
    def load(cls):
        s = cls()
        try:
            with open(cls.path(), encoding="utf-8") as f:
                d = json.load(f)
            for fl in fields(cls):
                if fl.name in d and isinstance(d[fl.name], type(getattr(s, fl.name))):
                    setattr(s, fl.name, d[fl.name])
        except (OSError, ValueError):
            pass
        return s

    def save(self):
        try:
            with open(self.path(), "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, ensure_ascii=False)
        except OSError:
            pass

    def sound_args(self):
        return ["--meter", self.meter, "--subdivision", str(self.subdivision), "--sound", self.sound,
                "--accent-note", note_name(self.accentNote), "--beat-note", note_name(self.beatNote),
                "--accent", "1" if self.accentDownbeat else "0", "--volume", f"{self.volume:.2f}"]

    def timing_args(self):
        return self.sound_args() + ["--count-in", str(self.countInBars), "--tail-bars", str(self.tailBars),
                                    "--downbeat-shift", str(self.downbeatShift), "--nudge-ms", f"{self.nudgeMs:.1f}",
                                    "--min-bpm", str(int(self.minBPM)), "--max-bpm", str(int(self.maxBPM)),
                                    "--cache-dir", local_dir("cache"), "--lang", self.language]

    def render_args(self):
        return self.timing_args() + ["--format", self.format, "--bitrate", str(self.mp3Bitrate),
                                     "--midi-channel", str(self.midiChannel), "--layout", self.layout,
                                     "--song-volume", f"{self.songVolume:.2f}", "--preview", "1" if self.makePreview else "0"]

    def preview_args(self):
        return self.timing_args() + ["--volume", "1"]  # the player applies click volume live

    @property
    def ext(self):
        return "mid" if self.format == "midi" else self.format


def engine_command():
    """The installed app ships click_engine.exe (Python + madmom inside) next to Click Studio.exe."""
    if getattr(sys, "frozen", False):
        return [os.path.join(os.path.dirname(sys.executable), "click_engine.exe")]
    here = os.path.dirname(os.path.abspath(__file__))
    return [sys.executable, "-I", "-X", "utf8", os.path.join(here, "..", "engine", "click_engine.py")]


class LineProcess(QProcess):
    """Runs the engine and hands over its JSON lines."""
    line = Signal(dict)

    def __init__(self, args, parent=None):
        super().__init__(parent)
        cmd = engine_command() + args
        self.setProgram(cmd[0])
        self.setArguments(cmd[1:])
        env = self.processEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        self.setProcessEnvironment(env)
        self.setProcessChannelMode(QProcess.MergedChannels)
        self._buf = b""
        self.readyReadStandardOutput.connect(self._read)

    def _read(self):
        self._buf += bytes(self.readAllStandardOutput())
        while b"\n" in self._buf:
            raw, self._buf = self._buf.split(b"\n", 1)
            try:
                o = json.loads(raw.decode("utf-8", "replace").strip())
                if isinstance(o, dict):
                    self.line.emit(o)
            except ValueError:
                pass

    def stop(self):
        if self.state() != QProcess.NotRunning:
            self.kill()


class Job:
    def __init__(self, source):
        self.id = uuid.uuid4().hex
        self.source = source
        self.custom_name = ""
        self.status = "idle"  # idle queued running done failed cancelled
        self.stage = ""
        self.progress = 0.0
        self.result = {}
        self.error = ""
        self.destination = None

    @property
    def stem(self):
        return os.path.splitext(os.path.basename(self.source))[0]

    def default_name(self, layout):
        return self.stem + LAYOUT_SUFFIX[layout]

    def output_name(self, layout):
        n = self.custom_name.strip()
        for ch in '\\/:*?"<>|':
            n = n.replace(ch, "-")
        return n or self.default_name(layout)

    @property
    def active(self):
        return self.status == "running"

    @property
    def finished(self):
        return self.status in ("done", "failed", "cancelled")


class Player(QObject):
    """Plays the click and the song as two mono stems so volumes and channels change live."""
    changed = Signal()
    SR = 44100

    def __init__(self):
        super().__init__()
        self.job_id = None
        self.loading_id = None
        self.playing = False
        self.offset = 0.0
        self._click = self._song = None
        self._pos = 0
        self._stream = None
        self.cv, self.sv, self.pan = 0.9, 0.8, 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._tick)

    @property
    def duration(self):
        return 0.0 if self._click is None else len(self._click) / self.SR

    @property
    def position(self):
        return self._pos / self.SR

    @position.setter
    def position(self, t):
        self._pos = int(max(0.0, min(t, self.duration)) * self.SR)

    def load(self, folder, job_id):
        import soundfile as sf
        self._stop_stream()
        c, _ = sf.read(os.path.join(folder, "click.wav"), dtype="float32")
        s, _ = sf.read(os.path.join(folder, "song.wav"), dtype="float32")
        n = min(len(c), len(s))
        self._click, self._song = c[:n], s[:n]
        self.job_id = job_id
        self._pos = 0

    def apply(self, st):
        self.cv, self.sv = float(st.volume), float(st.songVolume)
        self.pan = 0.0 if st.layout == "click" else (-1.0 if st.layout == "LR" else 1.0)

    def _gains(self, pan):
        return (1.0, 1.0) if pan == 0 else ((1.0, 0.0) if pan < 0 else (0.0, 1.0))

    def _callback(self, out, frames, _time, _status):
        import numpy as np
        import sounddevice as sd
        a, b = self._pos, min(self._pos + frames, len(self._click))
        n = b - a
        cl, cr = self._gains(self.pan)
        sl, sr = self._gains(-self.pan)
        c, s = self._click[a:b] * self.cv, self._song[a:b] * self.sv
        out[:n, 0] = c * cl + s * sl
        out[:n, 1] = c * cr + s * sr
        out[n:] = 0
        np.clip(out, -1, 1, out=out)
        self._pos = b
        if b >= len(self._click):
            raise sd.CallbackStop

    def play(self, t=None):
        import sounddevice as sd
        self._stop_stream()
        if self._click is None:
            return
        if t is not None:
            self.position = min(t, max(0.0, self.duration - 0.05))
        self._stream = sd.OutputStream(samplerate=self.SR, channels=2, dtype="float32", callback=self._callback)
        self._stream.start()
        self.playing = True
        self.timer.start()
        self.changed.emit()

    def seek(self, t):
        if self.playing:
            self.play(t)
        else:
            self.position = t
            self.changed.emit()

    def pause(self):
        self._stop_stream()
        self.changed.emit()

    def stop(self):
        self._stop_stream()
        self.job_id = None
        self._click = self._song = None
        self._pos = 0
        self.changed.emit()

    def _tick(self):
        if self._stream is not None and not self._stream.active:
            self._stop_stream()
            self._pos = 0
        self.changed.emit()

    def _stop_stream(self):
        self.timer.stop()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self.playing = False


class EngineCheck(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.state, self.message = "checking", ""
        self._p = None

    def check(self):
        self.state, self.message = "checking", ""
        self.changed.emit()
        p = LineProcess(["--check"], self)
        ok = []

        def on_line(o):
            if o.get("event") == "ok":
                ok.append(True)
            elif o.get("message"):
                self.message = o["message"]

        p.line.connect(on_line)
        p.finished.connect(lambda *_: self._done(bool(ok)))
        p.errorOccurred.connect(lambda e: self._done(False) if e == QProcess.FailedToStart else None)
        self._p = p
        p.start()

    def _done(self, ok):
        if self.state != "checking":
            return
        self.state = "ready" if ok else "failed"
        if not ok and not self.message:
            self.message = L("Движок не запустился.", "The engine did not start.")
        self.changed.emit()


class Studio(QObject):
    """The render queue: several songs are analysed in parallel."""
    jobs_changed = Signal()      # added/removed
    job_changed = Signal(str)    # one job's status
    running_changed = Signal()
    preview_state = Signal(str)  # job id whose preview state changed
    demo_state = Signal()
    all_done = Signal()
    trial_changed = Signal()     # a trial click was used or given back
    trial_exhausted = Signal()   # a save was asked for with no trial clicks left


    def __init__(self):
        super().__init__()
        self.settings = Settings.load()
        LANG[0] = self.settings.language
        self.jobs = []
        self.running = False
        self.player = Player()
        self.player.apply(self.settings)
        self.preview_error = {}
        self.max_parallel = max(1, min(4, (os.cpu_count() or 4) // 3))
        self.processes = {}
        self.licensed = False  # set by the window once the key checks out
        self._trial_jobs = set()  # running renders that took a trial click
        self._preview_proc = None
        self._demo_proc = None
        self.previewing_demo = False
        self._last_key = " ".join(self.settings.preview_args())
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(350)
        self._preview_timer.timeout.connect(self._rerender_preview)
        shutil.rmtree(os.path.join(tempfile.gettempdir(), "clickstudio-previews"), ignore_errors=True)

    # ------------------------------------------------------------ list
    def job(self, jid):
        return next((j for j in self.jobs if j.id == jid), None)

    @property
    def finished_count(self):
        return sum(j.finished for j in self.jobs)

    @property
    def pending_count(self):
        return sum(j.status == "queued" for j in self.jobs)

    @property
    def overall_progress(self):
        if not self.jobs:
            return 0.0
        return sum(j.progress if j.active else (1.0 if j.finished else 0.0) for j in self.jobs) / len(self.jobs)

    def add(self, paths):
        known = {os.path.normcase(os.path.abspath(j.source)) for j in self.jobs}
        added = False
        for p in paths:
            if os.path.isdir(p):
                self.add(sorted(os.path.join(p, n) for n in os.listdir(p)))
                continue
            key = os.path.normcase(os.path.abspath(p))
            if os.path.splitext(p)[1][1:].lower() in AUDIO_EXT and key not in known and os.path.isfile(p):
                self.jobs.append(Job(os.path.abspath(p)))
                known.add(key)
                added = True
        if added:
            self.jobs_changed.emit()

    def remove(self, job):
        p = self.processes.pop(job.id, None)
        if p:
            p.stop()
            self._refund(job.id)
        if self.player.job_id == job.id:
            self.player.stop()
        self.jobs = [j for j in self.jobs if j.id != job.id]
        self.jobs_changed.emit()
        self._pump()

    def clear_finished(self):
        self.jobs = [j for j in self.jobs if not j.finished]
        self.jobs_changed.emit()

    def settings_changed(self):
        self.settings.save()
        self.player.apply(self.settings)
        key = " ".join(self.settings.preview_args())
        if key != self._last_key:
            self._last_key = key
            if self.player.job_id:
                self._preview_timer.start()

    # ------------------------------------------------------------ saving
    def save(self, job, folder):
        if job.active:
            return
        job.destination, job.status, job.progress = folder, "queued", 0.0
        self.job_changed.emit(job.id)
        self.running = True
        self.running_changed.emit()
        self._pump()

    def save_all(self, folder):
        for j in self.jobs:
            if not j.active:
                j.destination, j.status, j.progress = folder, "queued", 0.0
                self.job_changed.emit(j.id)
        self.running = True
        self.running_changed.emit()
        self._pump()

    def stop(self):
        self.running = False
        for jid, p in list(self.processes.items()):
            p.stop()
            self._refund(jid)
            j = self.job(jid)
            if j:
                j.status = "cancelled"
                self.job_changed.emit(jid)
        self.processes.clear()
        for j in self.jobs:
            if j.status == "queued":
                j.status = "idle"
                self.job_changed.emit(j.id)
        self.running_changed.emit()

    def _pump(self):
        if not self.running:
            return
        while len(self.processes) < self.max_parallel:
            nxt = next((j for j in self.jobs if j.status == "queued"), None)
            if not nxt:
                break
            if not self.licensed:  # trial: 3 saved clicks per computer, ever
                if lic.trial_left() <= 0:
                    for j in self.jobs:
                        if j.status == "queued":
                            j.status = "idle"
                            self.job_changed.emit(j.id)
                    self.trial_exhausted.emit()
                    break
                lic.set_trial_used(lic.trial_used() + 1)
                self._trial_jobs.add(nxt.id)
                self.trial_changed.emit()
            self._launch(nxt)
        if not self.processes:
            self.running = False
            self.running_changed.emit()
            self.all_done.emit()

    def _refund(self, jid):
        """A render that failed or was stopped does not use up a trial click."""
        if jid in self._trial_jobs:
            self._trial_jobs.discard(jid)
            lic.set_trial_used(lic.trial_used() - 1)
            self.trial_changed.emit()

    def _unique_name(self, base, folder):
        taken = {self.job(i).output_name(self.settings.layout) for i in self.processes if self.job(i)}
        name, n = base, 2
        while os.path.exists(os.path.join(folder, f"{name}.{self.settings.ext}")) or name in taken:
            name, n = f"{base} {n}", n + 1
        return name

    STAGES = {"decode": ("Декодирование", "Decoding"), "analyze": ("Нейросеть слушает доли", "Listening for beats"),
              "track": ("Ищу сильные доли", "Finding downbeats"), "render": ("Рендер клика", "Rendering click"),
              "preview": ("Сведение проверки", "Mixing check file")}

    def _launch(self, job):
        folder = job.destination or os.path.dirname(job.source)
        name = self._unique_name(job.output_name(self.settings.layout), folder)
        job.status, job.stage, job.progress, job.error = "running", L("Подготовка", "Preparing"), 0.02, ""
        self.job_changed.emit(job.id)
        p = LineProcess(["--input", job.source, "--output-dir", folder, "--name", name] + self.settings.render_args(), self)
        jid = job.id

        def on_line(o):
            j = self.job(jid)
            if not j:
                return
            ev = o.get("event")
            if ev == "progress":
                st = o.get("stage", "")
                j.stage = L(*self.STAGES[st]) if st in self.STAGES else st
                j.progress = float(o.get("value", 0))
            elif ev == "done":
                j.status, j.result = "done", o
            elif ev == "error":
                j.status, j.error = "failed", o.get("message") or L("Ошибка", "Error")
            self.job_changed.emit(jid)

        def on_exit(code, _st=None):
            if self.processes.get(jid) is not p:
                return
            self.processes.pop(jid, None)
            j = self.job(jid)
            if j and j.active:
                j.status = "failed"
                j.error = (L("Движок завершился без результата", "The engine finished without a result") if code == 0
                           else L(f"Ошибка анализа (код {code})", f"Analysis error (code {code})"))
                self.job_changed.emit(jid)
            if not j or j.status != "done":
                self._refund(jid)
            self._trial_jobs.discard(jid)
            self._pump()

        p.line.connect(on_line)
        p.finished.connect(on_exit)
        p.errorOccurred.connect(lambda e: on_exit(-1) if e == QProcess.FailedToStart else None)
        self.processes[jid] = p
        p.start()

    # ------------------------------------------------------------ listening before saving
    def toggle_preview(self, job):
        if self.player.job_id == job.id and self.player.loading_id != job.id:
            if self.player.playing:
                self.player.pause()
            else:
                self.player.play()
        else:
            self._render_preview(job, 0.0, True)

    def _rerender_preview(self):
        j = self.job(self.player.job_id) if self.player.job_id else None
        if j:
            self._render_preview(j, self.player.position - self.player.offset, self.player.playing)

    def _render_preview(self, job, song_time, autoplay):
        if self._preview_proc:
            self._preview_proc.stop()
        if self.player.job_id != job.id:
            self.player.stop()
        folder = os.path.join(tempfile.gettempdir(), "clickstudio-previews", uuid.uuid4().hex)
        jid = job.id
        self.player.loading_id = jid
        self.preview_error.pop(jid, None)
        self.preview_state.emit(jid)
        p = LineProcess(["--input", job.source, "--preview-dir", folder] + self.settings.preview_args(), self)
        info = {"offset": 0.0, "message": None}

        def on_line(o):
            if o.get("event") == "done":
                info["offset"] = float(o.get("offset", 0))
            elif o.get("event") == "error":
                info["message"] = o.get("message")

        def on_exit(code, _st=None):
            if self._preview_proc is not p or self.player.loading_id != jid:
                return  # superseded by a newer render
            self.player.loading_id = None
            if code != 0:
                self.preview_error[jid] = info["message"] or L("Не удалось подготовить прослушивание",
                                                               "Could not prepare the preview")
            else:
                try:
                    self.player.load(folder, jid)
                    self.player.offset = info["offset"]
                    self.player.apply(self.settings)
                    t = max(0.0, song_time + info["offset"])
                    if autoplay:
                        self.player.play(t)
                    else:
                        self.player.position = t
                except Exception as e:  # no audio device, unreadable stems
                    self.preview_error[jid] = str(e) or L("Нет звукового устройства", "No audio device")
            self.preview_state.emit(jid)
            self.player.changed.emit()

        p.line.connect(on_line)
        p.finished.connect(on_exit)
        p.errorOccurred.connect(lambda e: on_exit(-1) if e == QProcess.FailedToStart else None)
        self._preview_proc = p
        p.start()

    # ------------------------------------------------------------ click sound preview
    def preview_click(self):
        if self._demo_proc:
            self._demo_proc.stop()
        out = os.path.join(tempfile.gettempdir(), "clickstudio-demo.wav")
        p = LineProcess(["--demo", out] + self.settings.sound_args(), self)
        self.previewing_demo = True
        self.demo_state.emit()

        def on_exit(code, _st=None):
            if self._demo_proc is not p:
                return
            self.previewing_demo = False
            self.demo_state.emit()
            if code == 0:
                try:
                    import sounddevice as sd
                    import soundfile as sf
                    x, sr = sf.read(out, dtype="float32")
                    sd.play(x, sr)
                except Exception:
                    pass

        p.finished.connect(on_exit)
        self._demo_proc = p
        p.start()


def reveal(paths):
    """Show files in Explorer."""
    if not paths:
        return
    p = os.path.normpath(paths[0])
    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", p])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", p])
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(p)])
