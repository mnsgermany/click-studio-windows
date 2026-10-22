"""Click Studio for Windows: the window (port of the Mac app's SwiftUI views)."""
import math, os, sys, threading, time, webbrowser

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (QAction, QBrush, QColor, QDesktopServices, QFont, QGuiApplication, QIcon, QKeySequence,
                           QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QButtonGroup, QDialog, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton,
                               QScrollArea, QSizePolicy, QSlider, QStackedWidget, QToolButton, QVBoxLayout, QWidget)

import license as lic
from studio import (AUDIO_EXT, FORMATS, LANG, LAYOUTS, METERS, SOUND_GLYPH, SOUNDS, SUB_GLYPH, SUBDIVISIONS, L, Settings, Studio,
                    EngineCheck, format_caption, layout_caption, layout_title, meter_title, note_name, note_presets,
                    reveal, sound_title, sub_title)

C = dict(bg="#0B0B1A", surface="#15152A", raised="#1D1D36", stroke="rgba(255,255,255,20)", strong="rgba(255,255,255,41)",
         text="#F8FAFC", sec="#A5ADC2", muted="#6E7590", indigo="#6366F1", violet="#8B5CF6", accent="#22C55E",
         bright="#4ADE80", danger="#F87171", warning="#FBBF24", dark="#05210F")
FONT = "Segoe UI Variable Text, Segoe UI, Arial"


def res(*p):
    base = getattr(sys, "_MEIPASS", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    return os.path.join(base, "resources", *p)


QSS = f"""
* {{ font-family: {FONT}; color: {C['text']}; }}
QMainWindow, QDialog {{ background: {C['bg']}; }}
QToolTip {{ background: {C['raised']}; color: {C['text']}; border: 1px solid {C['strong']}; padding: 4px 6px; }}
QMenuBar {{ background: {C['bg']}; color: {C['sec']}; padding: 2px 6px; }}
QMenuBar::item {{ padding: 4px 10px; border-radius: 6px; background: transparent; }}
QMenuBar::item:selected {{ background: {C['raised']}; color: {C['text']}; }}
QMenu {{ background: {C['surface']}; border: 1px solid {C['strong']}; padding: 6px; border-radius: 10px; }}
QMenu::item {{ padding: 6px 22px 6px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {C['indigo']}; }}
QMenu::item:disabled {{ color: {C['muted']}; }}
QMenu::separator {{ height: 1px; background: {C['stroke']}; margin: 5px 8px; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {C['strong']}; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}
QLabel {{ background: transparent; }}
QLabel[role="muted"] {{ color: {C['muted']}; font-size: 11px; }}
QLabel[role="sec"] {{ color: {C['sec']}; font-size: 12px; }}
QLabel[role="section"] {{ color: {C['muted']}; font-size: 11px; font-weight: 600; }}
QLabel[role="danger"] {{ color: {C['danger']}; font-size: 12px; }}
QPushButton[kind="ghost"], QToolButton[kind="ghost"] {{ background: rgba(29,29,54,205); border: 1px solid {C['strong']};
    border-radius: 17px; padding: 0 14px; min-height: 34px; font-size: 13px; font-weight: 500; }}
QPushButton[kind="ghost"]:hover, QToolButton[kind="ghost"]:hover {{ background: {C['raised']}; border-color: rgba(255,255,255,70); }}
QPushButton[kind="ghost"]:pressed, QToolButton[kind="ghost"]:pressed {{ background: #262648; }}
QPushButton[kind="ghost"]:disabled, QToolButton[kind="ghost"]:disabled {{ color: {C['muted']}; border-color: {C['stroke']}; }}
QToolButton[kind="ghost"] {{ padding-right: 26px; }}
QToolButton[kind="ghost"]::menu-button {{ border: none; border-left: 1px solid {C['strong']}; width: 22px; }}
QToolButton[kind="ghost"]::menu-arrow {{ width: 8px; height: 8px; }}
QPushButton[kind="primary"] {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {C['bright']}, stop:1 {C['accent']});
    color: {C['dark']}; border: none; border-radius: 20px; padding: 0 20px; min-height: 40px; font-size: 14px; font-weight: 600; }}
QPushButton[kind="primary"]:hover {{ background: {C['bright']}; }}
QPushButton[kind="primary"]:disabled {{ background: {C['raised']}; color: {C['muted']}; }}
QPushButton[kind="link"] {{ background: transparent; border: none; color: {C['accent']}; font-size: 12px; font-weight: 600; padding: 0; }}
QPushButton[kind="link"]:hover {{ color: {C['bright']}; }}
QPushButton[kind="link"]:disabled {{ color: {C['muted']}; }}
QPushButton[kind="plain"] {{ background: transparent; border: none; color: {C['muted']}; font-size: 12px; padding: 0; text-align: left; }}
QPushButton[kind="plain"]:hover {{ color: {C['text']}; }}
QPushButton[kind="icon"] {{ background: transparent; border: none; border-radius: 15px; min-width: 30px; max-width: 30px;
    min-height: 30px; max-height: 30px; color: {C['sec']}; font-size: 14px; }}
QPushButton[kind="icon"]:hover {{ background: {C['raised']}; color: {C['text']}; }}
QPushButton[kind="round"] {{ background: {C['raised']}; border: 1px solid {C['stroke']}; border-radius: 13px;
    min-width: 26px; max-width: 26px; min-height: 26px; max-height: 26px; font-size: 13px; font-weight: 700; }}
QPushButton[kind="round"]:hover {{ border-color: {C['strong']}; }}
QPushButton[kind="round"]:disabled {{ color: {C['muted']}; }}
QPushButton[tile="true"] {{ background: rgba(29,29,54,140); border: 1px solid {C['stroke']}; border-radius: 10px; color: {C['sec']}; }}
QPushButton[tile="true"]:hover {{ background: {C['raised']}; }}
QPushButton[tile="true"][tint="accent"]:checked {{ background: rgba(34,197,94,41); border: 1.5px solid rgba(34,197,94,230); }}
QPushButton[tile="true"][tint="indigo"]:checked {{ background: rgba(99,102,241,41); border: 1.5px solid rgba(99,102,241,230); }}
QPushButton[tile="true"][tint="violet"]:checked {{ background: rgba(139,92,246,41); border: 1.5px solid rgba(139,92,246,230); }}
QPushButton[tile="true"]:checked QLabel[role="tileMain"] {{ color: {C['text']}; }}
QLabel[role="tileMain"] {{ color: {C['sec']}; }}
QLabel[role="tileSub"] {{ color: {C['muted']}; }}
QFrame#card {{ background: rgba(21,21,42,217); border: 1px solid {C['stroke']}; border-radius: 14px; }}
QFrame#row {{ background: rgba(21,21,42,217); border: 1px solid {C['stroke']}; border-radius: 14px; }}
QFrame#row[active="true"] {{ border-color: rgba(34,197,94,115); }}
QFrame#hline {{ background: {C['stroke']}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#inspector {{ background: rgba(21,21,42,115); border-left: 1px solid {C['stroke']}; }}
QFrame#bottom {{ background: rgba(11,11,26,153); border-top: 1px solid {C['stroke']}; }}
QLineEdit {{ background: transparent; border: 1px solid {C['stroke']}; border-radius: 8px; padding: 3px 8px;
    selection-background-color: {C['indigo']}; }}
QLineEdit:focus {{ border-color: rgba(34,197,94,180); background: rgba(11,11,26,180); }}
QLineEdit:disabled {{ color: {C['sec']}; }}
QLineEdit#name {{ font-size: 15px; font-weight: 600; border: none; background: transparent; padding: 0; }}
QFrame#nameBox {{ border: 1px solid {C['stroke']}; border-radius: 8px; }}
QFrame#nameBox[editing="true"] {{ border-color: rgba(34,197,94,180); background: rgba(11,11,26,180); }}
QLineEdit[role="field"] {{ background: {C['raised']}; border: 1px solid {C['strong']}; border-radius: 8px; padding: 6px 10px; font-size: 13px; }}
QSlider::groove:horizontal {{ height: 4px; background: {C['raised']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {C['accent']}; border-radius: 2px; }}
QSlider[tint="indigo"]::sub-page:horizontal {{ background: {C['indigo']}; }}
QSlider::handle:horizontal {{ background: #FFFFFF; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider::handle:horizontal:hover {{ background: {C['bright']}; }}
QPushButton[seg="true"] {{ background: transparent; border: none; border-radius: 6px; color: {C['sec']}; font-size: 12px;
    font-weight: 600; min-width: 38px; min-height: 24px; }}
QPushButton[seg="true"]:checked {{ background: {C['indigo']}; color: white; }}
QFrame#seg {{ background: {C['raised']}; border: 1px solid {C['stroke']}; border-radius: 8px; }}
QLabel#chip {{ border-radius: 11px; padding: 0 8px; min-height: 22px; max-height: 22px; font-size: 11px; font-weight: 600; }}
QLabel#badge {{ background: {C['raised']}; color: {C['sec']}; border-radius: 8px; padding: 1px 6px; font-size: 9px; font-weight: 700; }}
QLabel#trial {{ border-radius: 12px; padding: 3px 10px; font-size: 12px; font-weight: 600; }}
QLabel#code {{ font-family: Consolas, monospace; font-size: 22px; font-weight: 700; color: {C['text']};
    background: {C['raised']}; border: 1px solid {C['strong']}; border-radius: 10px; padding: 8px 14px; }}
"""


def lbl(text, role=None, size=None, weight=None, color=None, wrap=False):
    w = QLabel(text)
    if role:
        w.setProperty("role", role)
    css = []
    if size:
        css.append(f"font-size: {size}px")
    if weight:
        css.append(f"font-weight: {weight}")
    if color:
        css.append(f"color: {color}")
    if css:
        w.setStyleSheet("; ".join(css))
    w.setWordWrap(wrap)
    return w


def button(text, kind="ghost", slot=None, tip=None):
    b = QPushButton(text)
    b.setProperty("kind", kind)
    b.setCursor(Qt.PointingHandCursor)
    if slot:
        b.clicked.connect(slot)
    if tip:
        b.setToolTip(tip)
    return b


def hline():
    f = QFrame()
    f.setObjectName("hline")
    return f


def restyle(w):
    w.style().unpolish(w)
    w.style().polish(w)


def section(title, trailing=None):
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    t = lbl(title.upper(), "section")
    f = t.font()
    f.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
    t.setFont(f)
    row.addWidget(t)
    row.addStretch()
    if trailing:
        row.addWidget(trailing)
    return row


class Tile(QPushButton):
    def __init__(self, main, sub=None, tint="accent", main_size=13, sub_size=10, main_weight=600, height=46,
                 align=Qt.AlignCenter):
        super().__init__()
        self.setProperty("tile", True)
        self.setProperty("tint", tint)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        v = QVBoxLayout(self)
        v.setContentsMargins(12 if align & Qt.AlignLeft else 4, 2, 4, 2)
        v.setSpacing(1)
        for text, role, size, weight in ((main, "tileMain", main_size, main_weight), (sub, "tileSub", sub_size, 400)):
            if text is None:
                continue
            q = QLabel(text)
            q.setProperty("role", role)
            q.setStyleSheet(f"font-size: {size}px; font-weight: {weight};")
            q.setAlignment(align)
            q.setWordWrap(role == "tileSub")
            q.setAttribute(Qt.WA_TransparentForMouseEvents)
            v.addWidget(q)

    def checkStateSet(self):
        super().checkStateSet()
        for q in self.findChildren(QLabel):
            restyle(q)

    def nextCheckState(self):
        super().nextCheckState()
        for q in self.findChildren(QLabel):
            restyle(q)


class Switch(QAbstractButton):
    def __init__(self, checked=False):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(34, 20)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["accent"]) if self.isChecked() else QColor(C["raised"]))
        p.drawRoundedRect(QRectF(0, 0, 34, 20), 10, 10)
        if not self.isChecked():
            p.setPen(QPen(QColor(255, 255, 255, 41), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(0.5, 0.5, 33, 19), 9.5, 9.5)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("white"))
        x = 16 if self.isChecked() else 2
        p.drawEllipse(QRectF(x, 2, 16, 16))


class Segmented(QFrame):
    changed = Signal(str)

    def __init__(self, items, value):
        super().__init__()
        self.setObjectName("seg")
        h = QHBoxLayout(self)
        h.setContentsMargins(2, 2, 2, 2)
        h.setSpacing(2)
        self.group = QButtonGroup(self)
        for key, title in items:
            b = QPushButton(title)
            b.setProperty("seg", True)
            b.setCheckable(True)
            b.setChecked(key == value)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self.group.addButton(b)
            h.addWidget(b)


class Card(QFrame):
    def __init__(self, padding=12):
        super().__init__()
        self.setObjectName("card")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(padding, padding, padding, padding)
        self.v.setSpacing(10)


def logo_pixmap(size):
    pm = QPixmap(res("AppIcon-1024.png"))
    if pm.isNull():
        pm = QPixmap(size, size)
        pm.fill(QColor(C["indigo"]))
    return pm.scaled(size * 2, size * 2, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class Logo(QLabel):
    def __init__(self, size=44):
        super().__init__()
        pm = logo_pixmap(size)
        pm.setDevicePixelRatio(2)
        self.setPixmap(pm)
        self.setFixedSize(size, size)


class Backdrop(QWidget):
    def paintEvent(self, _):
        p = QPainter(self)
        r = self.rect()
        p.fillRect(r, QColor(C["bg"]))
        g = QRadialGradient(QPointF(0, 0), 700)
        g.setColorAt(0, QColor(99, 102, 241, 72))
        g.setColorAt(1, QColor(99, 102, 241, 0))
        p.fillRect(r, QBrush(g))
        g2 = QRadialGradient(QPointF(r.width(), r.height()), 600)
        g2.setColorAt(0, QColor(34, 197, 94, 26))
        g2.setColorAt(1, QColor(34, 197, 94, 0))
        p.fillRect(r, QBrush(g2))


class PulseRings(QWidget):
    """Empty state: a big target with rings pulsing at 120 BPM."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(200, 200)
        self.targeted = False
        self.t0 = time.monotonic()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(100, 100)
        tint = QColor(C["accent"] if self.targeted else C["indigo"])
        t = time.monotonic() - self.t0
        for k in range(3):
            phase = ((t / 0.5) + k / 3) % 1
            r = 44 + phase * (100 - 44)
            col = QColor(tint)
            col.setAlphaF((1 - phase) * 0.45)
            p.setPen(QPen(col, 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(c, r, r)
        glow = QRadialGradient(c, 66)
        gc = QColor(tint)
        gc.setAlpha(110)
        glow.setColorAt(0.55, gc)
        gc.setAlpha(0)
        glow.setColorAt(1, gc)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(c, 66, 66)
        g = QLinearGradient(58, 58, 142, 142)
        if self.targeted:
            g.setColorAt(0, QColor(C["bright"]))
            g.setColorAt(1, QColor(C["accent"]))
        else:
            g.setColorAt(0, QColor(C["indigo"]))
            g.setColorAt(1, QColor(C["violet"]))
        p.setBrush(QBrush(g))
        p.drawEllipse(c, 42, 42)
        p.setPen(QPen(QColor("white"), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if self.targeted:  # arrow down
            p.drawLine(QPointF(100, 84), QPointF(100, 116))
            p.drawLine(QPointF(88, 105), QPointF(100, 117))
            p.drawLine(QPointF(112, 105), QPointF(100, 117))
        else:  # waveform with a plus
            xs = [78, 85, 92, 99, 106]
            hs = [8, 18, 26, 14, 20]
            for x, h in zip(xs, hs):
                p.drawLine(QPointF(x, 100 - h / 2), QPointF(x, 100 + h / 2))
            p.drawLine(QPointF(117, 94), QPointF(117, 110))
            p.drawLine(QPointF(109, 102), QPointF(125, 102))


class DropZone(QFrame):
    def __init__(self, win):
        super().__init__()
        self.targeted = False
        v = QVBoxLayout(self)
        v.setContentsMargins(32, 32, 32, 32)
        v.setSpacing(0)
        v.addStretch()
        self.rings = PulseRings()
        v.addWidget(self.rings, 0, Qt.AlignHCenter)
        v.addSpacing(22)
        self.title = lbl(L("Перетащите песни сюда", "Drag songs here"), size=22, weight=600)
        self.title.setAlignment(Qt.AlignCenter)
        v.addWidget(self.title)
        v.addSpacing(8)
        sub = lbl(L("Сколько угодно файлов или целую папку. MP3, WAV, FLAC, M4A, AIFF, OGG.",
                    "Any number of files or a whole folder. MP3, WAV, FLAC, M4A, AIFF, OGG."), "sec", size=13, wrap=True)
        sub.setAlignment(Qt.AlignCenter)
        sub.setFixedWidth(380)
        sub.setMinimumHeight(sub.heightForWidth(380))
        v.addWidget(sub, 0, Qt.AlignHCenter)
        v.addSpacing(22)
        v.addWidget(button("🗀  " + L("Выбрать файлы", "Choose files"), slot=win.open_files), 0, Qt.AlignHCenter)
        v.addSpacing(26)
        feats = QHBoxLayout()
        feats.setSpacing(18)
        feats.addStretch()
        for g, t in (("∿", L("Следит за ускорениями", "Follows tempo changes")), ("①", L("Находит сильную долю", "Finds the downbeat")),
                     ("▷", L("Слушаете до сохранения", "Listen before saving"))):
            feats.addWidget(lbl(f"{g}  {t}", size=12, weight=500, color=C["muted"]))
        feats.addStretch()
        v.addLayout(feats)
        v.addStretch()

    def set_targeted(self, t):
        self.targeted = t
        self.rings.targeted = t
        self.title.setText(L("Отпустите — начнём", "Drop to start") if t else L("Перетащите песни сюда", "Drag songs here"))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(21, 21, 42, 242 if self.targeted else 153))
        p.drawRoundedRect(r, 24, 24)
        pen = QPen(QColor(C["accent"]) if self.targeted else QColor(255, 255, 255, 41), 2 if self.targeted else 1.2)
        pen.setDashPattern([9 / pen.widthF(), 7 / pen.widthF()])
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 24, 24)


class StatusOrb(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(46, 46)
        self.status, self.progress = "idle", 0.0

    def set(self, status, progress):
        self.status, self.progress = status, progress
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, 46, 46)
        p.setPen(Qt.NoPen)
        if self.status == "done":
            g = QLinearGradient(0, 0, 46, 46)
            g.setColorAt(0, QColor(C["bright"]))
            g.setColorAt(1, QColor(C["accent"]))
            p.setBrush(QBrush(g))
        elif self.status == "failed":
            p.setBrush(QColor(248, 113, 113, 217))
        elif self.status == "running":
            p.setBrush(QColor(34, 197, 94, 31))
        else:
            p.setBrush(QColor(C["raised"]))
        p.drawEllipse(r)
        f = QFont()
        f.setPixelSize(18)
        f.setBold(True)
        p.setFont(f)
        if self.status == "running":
            p.setPen(QPen(QColor(255, 255, 255, 20), 3))
            p.drawEllipse(r.adjusted(4.5, 4.5, -4.5, -4.5))
            p.setPen(QPen(QColor(C["bright"]), 3, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(r.adjusted(4.5, 4.5, -4.5, -4.5), 90 * 16, -int(360 * 16 * max(0.03, self.progress)))
            p.setPen(QColor(C["bright"]))
            p.drawText(r, Qt.AlignCenter, "∿")
        elif self.status == "done":
            p.setPen(QPen(QColor(C["dark"]), 2.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            path = QPainterPath(QPointF(15, 24))
            path.lineTo(20.5, 29.5)
            path.lineTo(31, 17.5)
            p.drawPath(path)
        elif self.status == "failed":
            p.setPen(QColor("white"))
            p.drawText(r, Qt.AlignCenter, "!")
        else:
            p.setPen(QColor(C["sec"]))
            p.drawText(r, Qt.AlignCenter, "♪")


class ProgressStrip(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(3)
        self.value = 0.0

    def set(self, v):
        self.value = v
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(255, 255, 255, 20))
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0, QColor(C["bright"]))
        g.setColorAt(1, QColor(C["accent"]))
        p.fillRect(QRectF(0, 0, self.width() * self.value, 3), QBrush(g))


def chip(text, tint, fg=None):
    q = QLabel(text)
    q.setObjectName("chip")
    c = QColor(tint)
    q.setStyleSheet(f"background: rgba({c.red()},{c.green()},{c.blue()},38); color: {fg or tint};")
    return q


def fmt_time(t):
    t = int(max(0, t))
    return f"{t // 60}:{t % 60:02d}"


class PlayerStrip(QWidget):
    """Transport under the song that is loaded in the player."""

    def __init__(self, studio):
        super().__init__()
        self.studio = studio
        h = QHBoxLayout(self)
        h.setContentsMargins(16, 0, 16, 12)
        h.setSpacing(10)
        self.pos = lbl("0:00", size=11, weight=500, color=C["sec"])
        self.pos.setFixedWidth(44)
        self.pos.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setCursor(Qt.PointingHandCursor)
        self.dur = lbl("0:00", size=11, weight=500, color=C["sec"])
        self.dur.setFixedWidth(44)
        self.to_start = button(L("К началу песни", "To song start"), "plain",
                               lambda: studio.player.seek(max(0.0, studio.player.offset - 2)))
        for w in (self.pos, self.slider, self.dur, self.to_start):
            h.addWidget(w)
        self.slider.sliderReleased.connect(self._release)
        self.slider.sliderMoved.connect(lambda v: self.pos.setText(fmt_time(v / 1000 * self.studio.player.duration)))
        self.refresh()

    def _release(self):
        self.studio.player.seek(self.slider.value() / 1000 * self.studio.player.duration)

    def refresh(self):
        pl = self.studio.player
        d = max(1.0, pl.duration)
        if not self.slider.isSliderDown():
            self.slider.setValue(int(pl.position / d * 1000))
            self.pos.setText(fmt_time(pl.position))
        self.dur.setText(fmt_time(pl.duration))
        self.to_start.setVisible(pl.offset > 0.01)


class JobRow(QFrame):
    def __init__(self, win, job):
        super().__init__()
        self.win, self.studio, self.job = win, win.studio, job
        self.setObjectName("row")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        top = QHBoxLayout()
        top.setContentsMargins(16, 14, 16, 14)
        top.setSpacing(14)
        self.orb = StatusOrb()
        top.addWidget(self.orb, 0, Qt.AlignVCenter)
        mid = QVBoxLayout()
        mid.setSpacing(6)
        r1 = QHBoxLayout()
        r1.setSpacing(8)
        src = lbl(os.path.basename(job.source), size=12, color=C["muted"])
        src.setMaximumWidth(420)
        src.setToolTip(job.source)
        r1.addWidget(src)
        badge = QLabel(os.path.splitext(job.source)[1][1:].upper())
        badge.setObjectName("badge")
        r1.addWidget(badge)
        r1.addStretch()
        mid.addLayout(r1)
        self.name_box = QFrame()
        self.name_box.setObjectName("nameBox")
        self.name_box.setMaximumWidth(460)
        self.name_box.setFixedHeight(30)
        nb = QHBoxLayout(self.name_box)
        nb.setContentsMargins(8, 0, 8, 0)
        nb.setSpacing(4)
        nb.addWidget(lbl("✎", size=12, color=C["muted"]))
        self.name = QLineEdit(job.custom_name)
        self.name.setObjectName("name")
        self.name.textChanged.connect(lambda t: setattr(job, "custom_name", t))
        self.name.installEventFilter(self)
        nb.addWidget(self.name, 1)
        self.ext = lbl("", size=15, weight=600, color=C["muted"])
        nb.addWidget(self.ext)
        mid.addWidget(self.name_box)
        self.status_host = QWidget()
        self.status_lay = QHBoxLayout(self.status_host)
        self.status_lay.setContentsMargins(0, 0, 0, 0)
        self.status_lay.setSpacing(6)
        mid.addWidget(self.status_host)
        top.addLayout(mid, 1)

        self.listen = button("", tip=L("Песня с кликом. Громкость и каналы меняются справа",
                                       "Song with click. Volumes and channels are on the right"))
        self.listen.clicked.connect(lambda: win.gated(lambda: self.studio.toggle_preview(job), listen=True))
        self.save = QToolButton()
        self.save.setProperty("kind", "ghost")
        self.save.setCursor(Qt.PointingHandCursor)
        self.save.setText("⤓  " + L("Сохранить", "Save"))
        self.save.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.save.setPopupMode(QToolButton.MenuButtonPopup)
        self.save.setToolTip(L("Нажмите — сохранить рядом с песней. Стрелка — выбрать папку",
                               "Click to save next to the song. Arrow: choose a folder"))
        self.save.clicked.connect(lambda: win.gated(lambda: self.studio.save(job, None)))
        self.save_menu = QMenu(self.save)
        self.save_menu.aboutToShow.connect(self._fill_menu)
        self.save.setMenu(self.save_menu)
        self.folder_btn = button("🗀", "icon", lambda: reveal(job.result.get("files", [])), L("Показать в Проводнике", "Show in Explorer"))
        self.remove_btn = button("✕", "icon", lambda: self.studio.remove(job))
        for w in (self.listen, self.save, self.folder_btn, self.remove_btn):
            top.addWidget(w, 0, Qt.AlignVCenter)
        outer.addLayout(top)
        self.player_strip = PlayerStrip(self.studio)
        outer.addWidget(self.player_strip)
        self.progress = ProgressStrip()
        outer.addWidget(self.progress)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context)
        self.refresh()

    def eventFilter(self, obj, ev):
        if obj is self.name and ev.type() in (ev.Type.FocusIn, ev.Type.FocusOut):
            self.name_box.setProperty("editing", ev.type() == ev.Type.FocusIn)
            restyle(self.name_box)
        return False

    def _fill_menu(self):
        m, job = self.save_menu, self.job
        m.clear()
        m.addAction(L("Рядом с песней", "Next to the song"), lambda: self.win.gated(lambda: self.studio.save(job, None)))
        m.addAction(L("В папку…", "To folder…"), lambda: self.win.gated(lambda: self.win.choose_folder(lambda f: self.studio.save(job, f))))
        f = self.studio.settings.outputFolder
        if f:
            n = os.path.basename(f.rstrip("\\/")) or f
            m.addAction(L(f"В «{n}»", f"To “{n}”"), lambda: self.win.gated(lambda: self.studio.save(job, f)))

    def _context(self, pos):
        m = QMenu(self)
        m.addAction(L("Показать песню в Проводнике", "Show Song in Explorer"), lambda: reveal([self.job.source]))
        if self.job.status == "done":
            m.addAction(L("Показать клик в Проводнике", "Show Click in Explorer"), lambda: reveal(self.job.result.get("files", [])))
        m.addAction(L("Сбросить имя", "Reset Name"), lambda: self.name.setText(""))
        m.addSeparator()
        m.addAction(L("Убрать из списка", "Remove from List"), lambda: self.studio.remove(self.job))
        m.exec(self.mapToGlobal(pos))

    def refresh(self):
        job, st, pl = self.job, self.studio.settings, self.studio.player
        ready = self.win.engine.state == "ready"
        self.setProperty("active", job.active)
        restyle(self)
        self.orb.set(job.status, job.progress)
        self.name.setPlaceholderText(job.default_name(st.layout))
        self.name.setEnabled(not job.active)
        self.name_box.setToolTip(L(f"Имя файла. Оставьте пустым, и будет «{job.default_name(st.layout)}»",
                                   f"File name. Leave empty for “{job.default_name(st.layout)}”"))
        self.ext.setText("." + st.ext)
        loading = pl.loading_id == job.id
        playing = pl.job_id == job.id and pl.playing
        self.listen.setText("…" if loading else ("❚❚  " + L("Пауза", "Pause") if playing else "▶  " + L("Слушать", "Listen")))
        self.listen.setEnabled(not loading and ready)
        self.save.setEnabled(not job.active and ready)
        self.folder_btn.setVisible(job.status == "done")
        self.remove_btn.setText("■" if job.active else "✕")
        self.remove_btn.setToolTip(L("Остановить и убрать", "Stop and remove") if job.active else L("Убрать из списка", "Remove from list"))
        self.player_strip.setVisible(pl.job_id == job.id and pl.duration > 0)
        if self.player_strip.isVisible():
            self.player_strip.refresh()
        self.progress.setVisible(job.active)
        self.progress.set(job.progress)
        self._status_line()

    def _status_line(self):
        lay = self.status_lay
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        job, pl = self.job, self.studio.player
        s = job.status
        if s == "idle":
            e = self.studio.preview_error.get(job.id)
            if e:
                w = lbl("⚠ " + e, "danger", wrap=True)
            else:
                w = lbl(L("Готовлю прослушивание… (первый раз дольше)", "Preparing preview… (slower the first time)")
                        if pl.loading_id == job.id else L("Послушайте и сохраните", "Listen, then save"), "sec")
            lay.addWidget(w)
        elif s == "queued":
            lay.addWidget(lbl(L("В очереди", "Queued"), "sec"))
        elif s == "running":
            lay.addWidget(lbl(job.stage, size=12, weight=500, color=C["bright"]))
            lay.addWidget(lbl(f"{int(job.progress * 100)}%", size=12, weight=500, color=C["muted"]))
        elif s == "done":
            r = job.result
            lay.addWidget(chip(f"♩ {r.get('bpm', 0):.0f} BPM", C["accent"]))
            if r.get("bpm_max", 0) - r.get("bpm_min", 0) >= 3:
                lay.addWidget(chip(f"↕ {r['bpm_min']:.0f}–{r['bpm_max']:.0f}", C["warning"]))
            lay.addWidget(chip(f"♪ {r.get('meter', '')}", C["indigo"], "#A5B4FC"))
            if r.get("offset", 0) > 0.001:
                c = chip("→| " + L(f"песня с {r['offset']:.2f} с", f"song at {r['offset']:.2f} s"), C["violet"])
                c.setToolTip(L("Из-за отсчёта клик начинается раньше песни. Сдвиньте песню на это время в DAW.",
                               "The count-in starts the click before the song. Shift the song by this much in your DAW."))
                lay.addWidget(c)
        elif s == "failed":
            lay.addWidget(lbl("⚠ " + job.error, "danger", wrap=True))
        elif s == "cancelled":
            lay.addWidget(lbl(L("Остановлено", "Stopped"), size=12, color=C["muted"]))
        lay.addStretch()


class NoteStepper(QWidget):
    def __init__(self, title, value, on_change, enabled=True):
        super().__init__()
        self.value, self.on_change = value, on_change
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        h.addWidget(lbl(title, "sec"))
        h.addStretch()
        minus = button("−", "round", lambda: self.step(-1), L("На полтона ниже", "Semitone down"))
        h.addWidget(minus)
        box = QVBoxLayout()
        box.setSpacing(0)
        self.name = lbl("", size=16, weight=700)
        self.name.setAlignment(Qt.AlignCenter)
        self.midi = lbl("", size=9, color=C["muted"])
        self.midi.setAlignment(Qt.AlignCenter)
        box.addWidget(self.name)
        box.addWidget(self.midi)
        holder = QWidget()
        holder.setFixedWidth(58)
        holder.setLayout(box)
        h.addWidget(holder)
        h.addWidget(button("+", "round", lambda: self.step(1), L("На полтона выше", "Semitone up")))
        self.setEnabled(True)
        self.set_dim(not enabled)
        self.show_value()

    def set_dim(self, dim):
        eff = 0.5 if dim else 1.0
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        e = QGraphicsOpacityEffect(self)
        e.setOpacity(eff)
        self.setGraphicsEffect(e)

    def show_value(self):
        self.name.setText(note_name(self.value))
        self.midi.setText(f"MIDI {self.value}")

    def step(self, d):
        self.value = min(108, max(24, self.value + d))
        self.show_value()
        self.on_change(self.value)


class Counter(QWidget):
    """Stepper with − / + buttons (bars before/after, downbeat shift)."""

    def __init__(self, title, value, lo, hi, text, on_change, big=True):
        super().__init__()
        self.value, self.lo, self.hi, self.text, self.on_change = value, lo, hi, text, on_change
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        h.addWidget(lbl(title, "sec"))
        h.addStretch()
        self.label = lbl("", size=14 if big else 12, weight=700 if big else 600)
        self.label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.label.setMinimumWidth(36)
        h.addWidget(self.label)
        self.minus = button("−", "round", lambda: self.step(-1))
        self.plus = button("+", "round", lambda: self.step(1))
        h.addWidget(self.minus)
        h.addWidget(self.plus)
        self.show_value()

    def show_value(self):
        self.label.setText(self.text(self.value))
        self.minus.setEnabled(self.value > self.lo)
        self.plus.setEnabled(self.value < self.hi)

    def step(self, d):
        self.value = min(self.hi, max(self.lo, self.value + d))
        self.show_value()
        self.on_change(self.value)


class Inspector(QFrame):
    def __init__(self, win):
        super().__init__()
        self.win, self.studio = win, win.studio
        self.setObjectName("inspector")
        self.setFixedWidth(356)
        self.show_advanced = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(self.scroll)
        self.build()

    def set(self, **kw):
        for k, v in kw.items():
            setattr(self.studio.settings, k, v)
        self.studio.settings_changed()
        self.win.settings_changed()

    def rebuild(self):
        # deferred: the tile or switch that asked for it is still handling its click
        y = self.scroll.verticalScrollBar().value()

        def go():
            self.build()
            QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(y))
        QTimer.singleShot(0, go)

    def tiles(self, items, current, on_pick, cols, **tile_kw):
        grid = QGridLayout()
        grid.setSpacing(8)
        group = QButtonGroup(self)
        for i, (key, main, sub) in enumerate(items):
            t = Tile(main, sub, **tile_kw)
            t.setChecked(key == current)
            t.clicked.connect(lambda _=False, k=key: on_pick(k))
            group.addButton(t)
            grid.addWidget(t, i // cols, i % cols)
        return grid

    def build(self):
        s = self.studio.settings
        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(22, 30, 22, 28)
        v.setSpacing(22)
        v.addWidget(lbl(L("Настройки клика", "Click settings"), size=17, weight=700))

        def block(title, trailing=None):
            b = QVBoxLayout()
            b.setSpacing(10)
            b.addLayout(section(title, trailing))
            v.addLayout(b)
            return b

        # output: click alone or click + song in separate channels
        b = block(L("Что сохранять", "What to save"))

        def pick_layout(o):
            kw = {"layout": o}
            if o != "click" and s.format == "midi":
                kw["format"] = "wav"
            self.set(**kw)
            self.rebuild()
        b.addLayout(self.tiles([(o, layout_title(o), layout_caption(o)) for o in LAYOUTS], s.layout, pick_layout, 1,
                               tint="indigo", sub_size=10, height=46, align=Qt.AlignLeft | Qt.AlignVCenter))

        # volumes: live while listening, and used when saving
        b = block(L("Громкость", "Volume"))
        for key, glyph, title in (("volume", "♩", L("Клик", "Click")), ("songVolume", "♪", L("Песня", "Song"))):
            row = QHBoxLayout()
            row.setSpacing(10)
            g = lbl(glyph, size=13, color=C["muted"])
            g.setFixedWidth(16)
            row.addWidget(g)
            t = lbl(title, "sec")
            t.setFixedWidth(52)
            row.addWidget(t)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(0, 100)
            sl.setValue(int(round(getattr(s, key) * 100)))
            sl.setCursor(Qt.PointingHandCursor)
            pct = lbl(f"{sl.value()}%", size=11, weight=600, color=C["sec"])
            pct.setFixedWidth(36)
            pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            sl.valueChanged.connect(lambda val, k=key, p=pct: (p.setText(f"{val}%"), self.set(**{k: val / 100})))
            row.addWidget(sl, 1)
            row.addWidget(pct)
            holder = QWidget()
            holder.setLayout(row)
            if key == "songVolume" and s.layout == "click":
                from PySide6.QtWidgets import QGraphicsOpacityEffect
                e = QGraphicsOpacityEffect(holder)
                e.setOpacity(0.6)
                holder.setGraphicsEffect(e)
            b.addWidget(holder)
        b.addWidget(lbl(L("Песня звучит только при прослушивании и в файл не попадает",
                          "The song plays only while listening and is not saved") if s.layout == "click" else
                        L("Меняйте во время прослушивания: так и сохранится", "Adjust while listening; it is saved the same way"),
                        "muted", wrap=True))

        # format
        b = block(L("Формат", "Format"))
        fmts = [f for f in FORMATS if s.layout == "click" or f != "midi"]
        b.addLayout(self.tiles([(f, f.upper(), format_caption(f)) for f in fmts], s.format,
                               lambda f: (self.set(format=f), self.rebuild()), len(fmts),
                               main_size=15, main_weight=700, sub_size=9, height=62))
        if s.format == "mp3":
            row = QHBoxLayout()
            row.addWidget(lbl(L("Битрейт", "Bitrate"), "sec"))
            row.addStretch()
            seg = Segmented([(str(k), f"{k}") for k in (192, 256, 320)], str(s.mp3Bitrate))
            seg.changed.connect(lambda k: self.set(mp3Bitrate=int(k)))
            row.addWidget(seg)
            row.addWidget(lbl("kbps", "muted"))
            b.addLayout(row)
        if s.format == "midi":
            row = QHBoxLayout()
            row.addWidget(lbl(L("MIDI-канал", "MIDI channel"), "sec"))
            row.addStretch()
            seg = Segmented([("10", L("10 · ударные", "10 · drums")), ("1", L("1 · мелодия", "1 · melodic"))], str(s.midiChannel))
            seg.changed.connect(lambda k: self.set(midiChannel=int(k)))
            row.addWidget(seg)
            b.addLayout(row)

        # meter
        b = block(L("Размер", "Meter"))

        def pick_meter(m):
            kw = {"meter": m}
            if m in ("6/8", "12/8"):
                kw["subdivision"] = 3
            self.set(**kw)
            self.rebuild()
        b.addLayout(self.tiles([(m, meter_title(m), None) for m in METERS], s.meter, pick_meter, 4, tint="indigo",
                               main_size=14, height=36))
        b.addWidget(lbl(L("Определю 3/4 или 4/4 по самой песне", "Detects 3/4 or 4/4 from the song") if s.meter == "auto"
                        else L("Сильная доля ищется в заданном размере", "Downbeats are found in this meter"), "muted", wrap=True))

        # subdivision
        b = block(L("Ноты", "Notes"))
        b.addLayout(self.tiles([(d, SUB_GLYPH[d], sub_title(d)) for d in SUBDIVISIONS], s.subdivision,
                               lambda d: self.set(subdivision=d), 4, main_size=20, main_weight=400, sub_size=10, height=58))

        # sound
        self.demo_btn = button("▶  " + (L("…", "…") if self.studio.previewing_demo else L("Прослушать", "Preview")), "link",
                               self.studio.preview_click, L("Два такта выбранным звуком (Ctrl+P)", "Two bars of this sound (Ctrl+P)"))
        self.demo_btn.setEnabled(self.win.engine.state == "ready")
        b = block(L("Звук клика", "Click sound"), self.demo_btn)

        def pick_sound(k):
            self.set(sound=k)
            if self.win.engine.state == "ready":
                self.studio.preview_click()
        b.addLayout(self.tiles([(k, SOUND_GLYPH[k], sound_title(k)) for k in SOUNDS], s.sound, pick_sound, 3, tint="violet",
                               main_size=18, main_weight=600, sub_size=11, height=62))

        # pitch
        presets = QPushButton(L("Пресеты", "Presets") + " ▾")
        presets.setProperty("kind", "link")
        presets.setCursor(Qt.PointingHandCursor)
        pm = QMenu(presets)
        for title, a, bt in note_presets():
            pm.addAction(title, lambda a=a, bt=bt: (self.set(accentNote=a, beatNote=bt), self.rebuild()))
        presets.clicked.connect(lambda: pm.exec(presets.mapToGlobal(presets.rect().bottomLeft())))
        b = block(L("Высота нот", "Pitch"), presets)
        card = Card()
        card.v.addWidget(NoteStepper(L("Сильная доля", "Downbeat"), s.accentNote, lambda n: self.set(accentNote=n),
                                     s.accentDownbeat))
        card.v.addWidget(hline())
        card.v.addWidget(NoteStepper(L("Остальные доли", "Other beats"), s.beatNote, lambda n: self.set(beatNote=n)))
        b.addWidget(card)
        row = QHBoxLayout()
        sw = Switch(s.accentDownbeat)
        sw.toggled.connect(lambda on: (self.set(accentDownbeat=on), self.rebuild()))
        row.addWidget(sw)
        row.addWidget(lbl(L("Акцент на первую долю такта", "Accent the first beat of the bar"), "sec"))
        row.addStretch()
        b.addLayout(row)

        # bars of click before and after the song
        b = block(L("Клик до и после песни", "Click before and after"))
        card = Card()
        bars = lambda n: L("нет", "none") if n == 0 else str(n)  # noqa: E731
        card.v.addWidget(Counter(L("Тактов до песни", "Bars before"), s.countInBars, 0, 16, bars, lambda n: self.set(countInBars=n)))
        card.v.addWidget(hline())
        card.v.addWidget(Counter(L("Тактов после песни", "Bars after"), s.tailBars, 0, 16, bars, lambda n: self.set(tailBars=n)))
        b.addWidget(card)
        b.addWidget(lbl(L("0 — без клика. Отсчёт идёт в темпе начала, хвост — в темпе конца",
                          "0 means none. The count-in uses the opening tempo, the tail the closing one"), "muted", wrap=True))

        # advanced
        adv = QVBoxLayout()
        adv.setSpacing(12)
        tog = QPushButton()
        tog.setProperty("kind", "plain")
        tog.setCursor(Qt.PointingHandCursor)
        tl = QHBoxLayout(tog)
        tl.setContentsMargins(0, 0, 0, 0)
        t = lbl(L("Тонкая настройка", "Fine tuning").upper() + ("   ▾" if self.show_advanced else "   ▸"), "section")
        f = t.font()
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        t.setFont(f)
        t.setAttribute(Qt.WA_TransparentForMouseEvents)
        tl.addWidget(t)
        tog.setFixedHeight(20)
        tog.clicked.connect(lambda: (setattr(self, "show_advanced", not self.show_advanced), self.rebuild()))
        adv.addWidget(tog)
        if self.show_advanced:
            def shift_text(n):
                return L("как нашёл", "as found") if n == 0 else (f"+{n} " if n > 0 else f"{n} ") + L("доля", "beat")
            c = Counter(L("Сдвиг сильной доли", "Downbeat shift"), s.downbeatShift, -3, 3, shift_text,
                        lambda n: self.set(downbeatShift=n), big=False)
            c.setToolTip(L("Если «раз» попал не туда, сдвиньте его на одну-две доли", "If “one” landed wrong, shift it by a beat or two"))
            adv.addWidget(c)
            row = QHBoxLayout()
            row.addWidget(lbl(L("Коррекция", "Nudge"), "sec"))
            row.addStretch()
            sl = QSlider(Qt.Horizontal)
            sl.setProperty("tint", "indigo")
            sl.setRange(-50, 50)
            sl.setValue(int(s.nudgeMs))
            sl.setFixedWidth(110)
            ms = lbl(f"{int(s.nudgeMs)} " + L("мс", "ms"), size=11, weight=600, color=C["sec"])
            ms.setFixedWidth(46)
            ms.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            sl.valueChanged.connect(lambda val: (ms.setText(f"{val} " + L("мс", "ms")), self.set(nudgeMs=float(val))))
            row.addWidget(sl)
            row.addWidget(ms)
            w = QWidget()
            w.setLayout(row)
            w.setToolTip(L("Сдвинуть весь клик раньше (−) или позже (+)", "Move the whole click earlier (−) or later (+)"))
            adv.addWidget(w)
            row = QHBoxLayout()
            row.addWidget(lbl(L("Темп, BPM", "Tempo, BPM"), "sec"))
            row.addStretch()
            for key in ("minBPM", "maxBPM"):
                e = QLineEdit(str(int(getattr(s, key))))
                e.setProperty("role", "field")
                e.setFixedWidth(52)
                e.setAlignment(Qt.AlignCenter)

                def commit(e=e, key=key):
                    try:
                        val = float(e.text())
                        if 20 <= val <= 400:
                            self.set(**{key: val})
                            return
                    except ValueError:
                        pass
                    e.setText(str(int(getattr(self.studio.settings, key))))
                e.editingFinished.connect(commit)
                row.addWidget(e)
                if key == "minBPM":
                    row.addWidget(lbl("–", color=C["muted"]))
            w = QWidget()
            w.setLayout(row)
            w.setToolTip(L("Сузьте диапазон, если клик попадает в половинный или двойной темп",
                           "Narrow it if the click lands at half or double tempo"))
            adv.addWidget(w)
            row = QHBoxLayout()
            sw = Switch(s.makePreview)
            sw.toggled.connect(lambda on: self.set(makePreview=on))
            row.addWidget(sw)
            col = QVBoxLayout()
            col.setSpacing(1)
            col.addWidget(lbl(L("Файл проверки", "Check file"), size=12, weight=500))
            col.addWidget(lbl(L("Песня + клик в одном MP3", "Song + click in one MP3"), "muted"))
            row.addLayout(col)
            row.addStretch()
            adv.addLayout(row)

            def reset():
                fresh = Settings()
                fresh.language, fresh.outputFolder = s.language, s.outputFolder
                self.studio.settings = fresh
                self.studio.settings_changed()
                self.win.settings_changed()
                self.rebuild()
            adv.addWidget(button(L("Сбросить настройки", "Reset settings"), "plain", reset))
        v.addLayout(adv)
        v.addStretch()
        self.scroll.setWidget(body)

    def refresh_demo(self):
        try:
            self.demo_btn.setText("▶  " + ("…" if self.studio.previewing_demo else L("Прослушать", "Preview")))
            self.demo_btn.setEnabled(self.win.engine.state == "ready")
        except RuntimeError:
            pass


class LicenseDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle(L("Лицензия", "Licence"))
        self.setFixedWidth(560)
        self.setStyleSheet(f"QDialog {{ background: {C['surface']}; }}")
        v = QVBoxLayout(self)
        v.setContentsMargins(30, 26, 30, 26)
        v.setSpacing(14)
        head = QHBoxLayout()
        head.setSpacing(14)
        head.addWidget(Logo(44))
        ht = QVBoxLayout()
        ht.setSpacing(2)
        ht.addWidget(lbl(L("Лицензия Click Studio", "Click Studio licence"), size=20, weight=700))
        self.state = lbl("", "sec", wrap=True)
        self.state.setFixedWidth(440)
        ht.addWidget(self.state)
        head.addLayout(ht, 1)
        v.addLayout(head)
        code = win.machine_code
        if win.licensed:
            v.addWidget(lbl(L(f"Лицензия активна. Оформлена на {win.license_email}.", f"The licence is active. Registered to {win.license_email}."),
                            size=14, weight=600, color=C["bright"], wrap=True))
            v.addWidget(lbl(L("Код компьютера", "Computer code"), "section"))
            c = QLabel(lic.pretty(code) if code else "…")
            c.setObjectName("code")
            c.setTextInteractionFlags(Qt.TextSelectableByMouse)
            v.addWidget(c, 0, Qt.AlignLeft)
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(button(L("Закрыть", "Close"), "primary", self.accept))
            v.addLayout(row)
            self.state.setText(L("Спасибо за покупку!", "Thank you for your purchase!"))
            return
        intro = lbl(L(f"Без лицензии можно сохранить {lic.TRIAL_RENDERS} клика. Это один раз, перезапуск не добавляет новых. "
                      "Слушать песни с кликом можно всегда. Лицензия привязана к этому компьютеру.",
                      f"Without a licence you can save {lic.TRIAL_RENDERS} clicks. This is a one-time allowance; "
                      "restarting does not add more. Listening is always free. The licence is bound to this computer."),
                    "sec", wrap=True)
        intro.setMinimumHeight(intro.heightForWidth(500))
        intro.setFixedWidth(500)
        v.addWidget(intro)
        steps = [L("В боте нажмите «Приобрести лицензию» и оплатите.", "In the bot, tap “Buy licence” and pay."),
                 L("Пришлите боту свой e-mail.", "Send the bot your e-mail."),
                 L("Пришлите файл запроса (кнопка ниже) или нажмите «Скопировать запрос» и вставьте в чат.",
                   "Send the request file (button below), or tap “Copy request” and paste it into the chat."),
                 L("Введите e-mail и полученный ключ и нажмите «Активировать».", "Enter the e-mail and the key you got, then tap “Activate”.")]
        card = Card(14)
        card.v.setSpacing(8)
        for i, t in enumerate(steps, 1):
            r = QHBoxLayout()
            r.setSpacing(10)
            n = lbl(str(i), size=12, weight=700, color="white")
            n.setFixedSize(22, 22)
            n.setAlignment(Qt.AlignCenter)
            n.setStyleSheet(f"background: {C['indigo']}; border-radius: 11px; font-size: 12px; font-weight: 700;")
            r.addWidget(n, 0, Qt.AlignTop)
            st = lbl(t, size=13, wrap=True)
            st.setFixedWidth(440)
            st.setMinimumHeight(st.heightForWidth(440))
            r.addWidget(st, 1)
            card.v.addLayout(r)
        v.addWidget(card)
        v.addWidget(lbl(L("Код компьютера", "Computer code"), "section"))
        self.code = QLabel(lic.pretty(code) if code else "…")
        self.code.setObjectName("code")
        self.code.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.code, 0, Qt.AlignLeft)
        row = QHBoxLayout()
        row.setSpacing(8)
        if lic.BOT_URL:
            row.addWidget(button(L("Открыть бота", "Open the bot"), slot=lambda: webbrowser.open(lic.BOT_URL)))
        row.addWidget(button(L("Сохранить файл запроса", "Save request file"), slot=self.save_request))
        row.addWidget(button(L("Скопировать запрос", "Copy request"), slot=self.copy_request))
        row.addStretch()
        v.addLayout(row)
        self.email = QLineEdit(win.license_email)
        self.email.setProperty("role", "field")
        self.email.setPlaceholderText("E-mail")
        self.key = QLineEdit()
        self.key.setProperty("role", "field")
        self.key.setPlaceholderText(L("Ключ", "Key"))
        v.addWidget(self.email)
        v.addWidget(self.key)
        self.msg = lbl("", "danger", wrap=True)
        self.msg.setFixedWidth(500)
        v.addWidget(self.msg)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button(L("Позже", "Later"), slot=self.reject))
        self.activate_btn = button(L("Активировать", "Activate"), "primary", self.activate)
        row.addWidget(self.activate_btn)
        v.addLayout(row)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(500)
        self.tick()

    def tick(self):
        left = lic.trial_left()
        self.state.setText(L(f"Пробный режим · осталось кликов: {left} из {lic.TRIAL_RENDERS}",
                             f"Trial · {left} of {lic.TRIAL_RENDERS} clicks left") if left > 0
                           else L("Пробные клики закончились. Чтобы сохранять клики, активируйте программу.",
                                  "The trial clicks are used up. Activate the app to save clicks."))
        if self.win.machine_code and hasattr(self, "code"):
            self.code.setText(lic.pretty(self.win.machine_code))

    def save_request(self):
        if not self.win.machine_code:
            return
        start = os.path.join(os.path.expanduser("~"), "Desktop", lic.REQUEST_NAME)
        path, _ = QFileDialog.getSaveFileName(self, L("Сохранить файл запроса", "Save request file"), start,
                                              f"Click Studio (*{lic.REQUEST_EXT})")
        if path:
            if not path.lower().endswith(lic.REQUEST_EXT):
                path += lic.REQUEST_EXT
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(lic.request_text(self.win.machine_code))
            self.msg.setStyleSheet(f"color: {C['bright']};")
            self.msg.setText(L("Файл сохранён: ", "Saved: ") + path)

    def copy_request(self):
        if self.win.machine_code:
            QGuiApplication.clipboard().setText(lic.request_line(self.win.machine_code))
            self.msg.setStyleSheet(f"color: {C['bright']};")
            self.msg.setText(L("Запрос скопирован. Вставьте его в чат с ботом.", "Request copied. Paste it into the bot chat."))

    def activate(self):
        email, key = self.email.text(), self.key.text()
        if not self.win.machine_code:
            return
        if lic.valid(email, key, self.win.machine_code):
            lic.save(email, key)
            self.win.set_licensed(lic.clean_email(email))
            QMessageBox.information(self, "Click Studio", L("Готово! Программа активирована.", "Done! The app is activated."))
            self.accept()
        else:
            self.msg.setStyleSheet(f"color: {C['danger']};")
            self.msg.setText(L("Ключ не подходит к этому e-mail и компьютеру. Проверьте, что e-mail тот же, что вы прислали боту.",
                               "The key doesn't match this e-mail and computer. Check that the e-mail is the one you sent the bot."))


class Overlay(QWidget):
    """Engine check: shown until the bundled engine answers."""

    def __init__(self, win):
        super().__init__(win.centralWidget())
        self.win = win
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet("background: rgba(0,0,0,140);")
        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignCenter)
        self.panel = QFrame()
        self.panel.setFixedWidth(520)
        self.panel.setStyleSheet(f"QFrame {{ background: {C['surface']}; border: 1px solid {C['strong']}; border-radius: 22px; }}"
                                 "QLabel { border: none; background: transparent; }")
        pv = QVBoxLayout(self.panel)
        pv.setContentsMargins(36, 36, 36, 36)
        pv.setSpacing(16)
        pv.addWidget(Logo(56), 0, Qt.AlignHCenter)
        self.title = lbl("", size=20, weight=700)
        self.title.setAlignment(Qt.AlignCenter)
        self.msg = lbl("", "danger", wrap=True)
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.msg.setFixedWidth(448)
        self.hint = lbl(L("Переустановите Click Studio из установщика.", "Reinstall Click Studio from the installer."), "sec")
        self.hint.setAlignment(Qt.AlignCenter)
        self.retry = button(L("Проверить ещё раз", "Check again"), slot=win.engine.check)
        for w in (self.title, self.msg, self.hint):
            pv.addWidget(w)
        pv.addWidget(self.retry, 0, Qt.AlignHCenter)
        v.addWidget(self.panel)
        self.refresh()

    def refresh(self):
        e = self.win.engine
        self.setVisible(e.state != "ready")
        failed = e.state == "failed"
        self.title.setText(L("Движок не запустился", "The engine did not start") if failed else L("Запускаю движок…", "Starting the engine…"))
        self.msg.setText(e.message if failed else "")
        self.msg.setVisible(failed)
        self.hint.setVisible(failed)
        self.retry.setVisible(failed)
        self.setGeometry(self.parentWidget().rect())
        self.raise_()


class MainWindow(QMainWindow):
    code_ready = Signal(str)

    def __init__(self):
        super().__init__()
        self.studio = Studio()
        self.engine = EngineCheck()
        self.setWindowTitle("Click Studio")
        self.setWindowIcon(QIcon(res("AppIcon.ico")) if os.path.exists(res("AppIcon.ico")) else QIcon(logo_pixmap(64)))
        self.setMinimumSize(1040, 700)
        self.resize(1240, 820)
        self.setAcceptDrops(True)
        self.rows = {}
        # licence: 3 saved clicks per computer without a key (kept across restarts), listening stays free
        self.machine_code = ""
        self.license_email, self.licensed = "", False
        self.code_ready.connect(self._got_code)
        threading.Thread(target=lambda: self.code_ready.emit(lic.machine_code()), daemon=True).start()

        self.studio.jobs_changed.connect(lambda: QTimer.singleShot(0, self.rebuild_queue))
        self.studio.job_changed.connect(self.refresh_row)
        self.studio.preview_state.connect(self.refresh_row)
        self.studio.running_changed.connect(self.refresh_bottom)
        self.studio.job_changed.connect(lambda _id: self.refresh_bottom())
        self.studio.demo_state.connect(lambda: self.inspector.refresh_demo())
        self.studio.all_done.connect(self.done_sound)
        self.studio.player.changed.connect(self.player_changed)
        self.engine.changed.connect(self.engine_changed)
        self._player_job = None
        self.build()
        self.studio.trial_changed.connect(self.trial_tick)
        self.studio.trial_exhausted.connect(lambda: QTimer.singleShot(0, self.show_license))
        self.engine.check()

    # ------------------------------------------------------------ licence
    def _got_code(self, code):
        self.machine_code = code
        email, key = lic.load()
        if email and lic.valid(email, key, code):
            self.set_licensed(email)

    def set_licensed(self, email):
        self.licensed, self.license_email = True, email
        self.studio.licensed = True
        self.trial_tick()

    def allowed(self):
        return self.licensed or lic.trial_left() > 0

    def gated(self, action, listen=False):
        # listening is free; saving takes a trial click (Studio counts them as renders start)
        if listen or self.allowed():
            action()
        else:
            self.show_license()

    def show_license(self):
        LicenseDialog(self).exec()

    def trial_tick(self):
        b = self.trial_badge
        if self.licensed:
            b.hide()
            return
        left = lic.trial_left()
        col = QColor(C["danger"] if left <= 1 else C["warning"])
        b.setStyleSheet(f"background: rgba({col.red()},{col.green()},{col.blue()},38); color: {col.name()};")
        b.setText(L(f"Пробный режим · кликов: {left} из {lic.TRIAL_RENDERS}", f"Trial · {left} of {lic.TRIAL_RENDERS} clicks")
                  if left > 0 else L("Пробный режим закончился", "Trial ended"))
        b.show()

    # ------------------------------------------------------------ layout
    def build(self):
        LANG[0] = self.studio.settings.language
        self.menuBar().clear()
        self.build_menus()
        root = Backdrop()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        main = QWidget()
        mv = QVBoxLayout(main)
        mv.setContentsMargins(0, 0, 0, 0)
        mv.setSpacing(0)
        mv.addWidget(self.build_header())
        self.stack = QStackedWidget()
        dz_host = QWidget()
        dl = QVBoxLayout(dz_host)
        dl.setContentsMargins(28, 0, 28, 24)
        self.drop = DropZone(self)
        dl.addWidget(self.drop)
        self.stack.addWidget(dz_host)
        self.queue_scroll = QScrollArea()
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.stack.addWidget(self.queue_scroll)
        mv.addWidget(self.stack, 1)
        mv.addWidget(self.build_bottom())
        h.addWidget(main, 1)
        self.inspector = Inspector(self)
        h.addWidget(self.inspector)
        self.overlay = Overlay(self)
        self.rebuild_queue()
        self.trial_tick()

    def build_menus(self):
        mb = self.menuBar()
        f = mb.addMenu(L("Файл", "File"))
        a = f.addAction(L("Добавить песни…", "Add Songs…"), self.open_files)
        a.setShortcut(QKeySequence("Ctrl+O"))
        f.addAction(L("Лицензия…", "Licence…"), self.show_license)
        f.addSeparator()
        f.addAction(L("Выход", "Exit"), self.close)
        r = mb.addMenu(L("Рендер", "Render"))
        self.act_save_all = r.addAction(L("Сохранить все рядом с песнями", "Save All Next to Songs"),
                                        lambda: self.gated(lambda: self.studio.save_all(None)))
        self.act_save_all.setShortcuts([QKeySequence("Ctrl+Return"), QKeySequence("Ctrl+Enter")])
        self.act_save_folder = r.addAction(L("Сохранить все в папку…", "Save All to Folder…"),
                                           lambda: self.gated(lambda: self.choose_folder(self.studio.save_all)))
        self.act_save_folder.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.act_stop = r.addAction(L("Остановить", "Stop"), self.studio.stop)
        self.act_stop.setShortcut(QKeySequence("Ctrl+."))
        r.addSeparator()
        self.act_demo = r.addAction(L("Прослушать звук клика", "Play Click Sound"), self.studio.preview_click)
        self.act_demo.setShortcut(QKeySequence("Ctrl+P"))
        r.addAction(L("Убрать готовые", "Clear Finished"), self.studio.clear_finished)
        hm = mb.addMenu(L("Справка", "Help"))
        hm.addAction(L("Лицензия…", "Licence…"), self.show_license)
        hm.addAction(L("О программе", "About"), lambda: QMessageBox.about(
            self, "Click Studio", L("Click Studio для Windows\nКлик, который дышит вместе с песней.",
                                    "Click Studio for Windows\nA click that breathes with the song.")))

    def build_header(self):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(28, 26, 28, 18)
        h.setSpacing(14)
        h.addWidget(Logo(44))
        t = QVBoxLayout()
        t.setSpacing(2)
        t.addWidget(lbl("Click Studio", size=24, weight=700))
        tag = lbl(L("Клик, который дышит вместе с песней", "A click that breathes with the song"), "sec", size=13)
        tag.setMinimumWidth(tag.sizeHint().width())
        t.addWidget(tag)
        h.addLayout(t)
        h.addStretch()
        self.trial_badge = QLabel()
        self.trial_badge.setObjectName("trial")
        self.trial_badge.setFixedHeight(26)
        self.trial_badge.setCursor(Qt.PointingHandCursor)
        self.trial_badge.mousePressEvent = lambda _e: self.show_license()
        self.trial_badge.setToolTip(L("Лицензия…", "Licence…"))
        h.addWidget(self.trial_badge)
        self.clear_btn = button(L("Убрать готовые", "Clear finished"), slot=self.studio.clear_finished)
        self.add_btn = button("＋  " + L("Добавить", "Add"), slot=self.open_files)
        h.addWidget(self.clear_btn)
        h.addWidget(self.add_btn)
        seg = Segmented([("ru", "RU"), ("en", "EN")], self.studio.settings.language)
        seg.setToolTip(L("Язык программы", "App language"))
        seg.changed.connect(self.set_language)
        seg.setFixedHeight(32)
        h.addWidget(seg)
        return w

    def build_bottom(self):
        w = QFrame()
        w.setObjectName("bottom")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.overall = ProgressStrip()
        v.addWidget(self.overall)
        h = QHBoxLayout()
        h.setContentsMargins(28, 14, 28, 14)
        h.setSpacing(12)
        self.folder_label = lbl("", size=12, color=C["muted"])
        h.addWidget(self.folder_label)
        h.addStretch()
        self.count_box = QWidget()
        cb = QVBoxLayout(self.count_box)
        cb.setContentsMargins(0, 0, 0, 0)
        cb.setSpacing(2)
        self.count_label = lbl("", size=13, weight=600)
        self.count_label.setAlignment(Qt.AlignRight)
        par = lbl(L(f"параллельно до {self.studio.max_parallel}", f"up to {self.studio.max_parallel} at once"), "muted")
        par.setAlignment(Qt.AlignRight)
        cb.addWidget(self.count_label)
        cb.addWidget(par)
        h.addWidget(self.count_box)
        self.stop_btn = button("■  " + L("Стоп", "Stop"), slot=self.studio.stop)
        self.save_folder_btn = button("🗀  " + L("Сохранить все в папку…", "Save all to folder…"),
                                      slot=lambda: self.gated(lambda: self.choose_folder(self.studio.save_all)))
        self.save_all_btn = button("⤓  " + L("Сохранить все рядом с песнями", "Save all next to songs"), "primary",
                                   lambda: self.gated(lambda: self.studio.save_all(None)))
        for b in (self.stop_btn, self.save_folder_btn, self.save_all_btn):
            h.addWidget(b)
        v.addLayout(h)
        return w

    # ------------------------------------------------------------ updates
    def set_language(self, lang):
        self.studio.settings.language = lang
        self.studio.settings_changed()
        QTimer.singleShot(0, self.build)

    def settings_changed(self):
        for r in self.rows.values():
            r.refresh()
        self.refresh_bottom()

    def rebuild_queue(self):
        has = bool(self.studio.jobs)
        self.stack.setCurrentIndex(1 if has else 0)
        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(28, 0, 28, 20)
        v.setSpacing(10)
        hdr = QHBoxLayout()
        hdr.setContentsMargins(4, 0, 4, 0)
        hdr.addLayout(section(L("Песни", "Songs") + f" · {len(self.studio.jobs)}"))
        v.addLayout(hdr)
        self.rows = {}
        for j in self.studio.jobs:
            r = JobRow(self, j)
            self.rows[j.id] = r
            v.addWidget(r)
        v.addStretch()
        y = self.queue_scroll.verticalScrollBar().value()
        self.queue_scroll.setWidget(body)
        QTimer.singleShot(0, lambda: self.queue_scroll.verticalScrollBar().setValue(y))
        self.refresh_bottom()

    def refresh_row(self, jid):
        r = self.rows.get(jid)
        if r:
            r.refresh()

    def player_changed(self):
        pl = self.studio.player
        for jid in {self._player_job, pl.job_id, pl.loading_id} - {None}:
            self.refresh_row(jid)
        self._player_job = pl.job_id

    def refresh_bottom(self):
        st, ready = self.studio, self.engine.state == "ready"
        has = bool(st.jobs)
        self.clear_btn.setVisible(has and st.finished_count > 0)
        self.add_btn.setVisible(has)
        f = st.settings.outputFolder
        self.folder_label.setVisible(bool(f))
        if f:
            self.folder_label.setText("🗀  " + (os.path.basename(f.rstrip("\\/")) or f))
            self.folder_label.setToolTip(L("Последняя выбранная папка: ", "Last chosen folder: ") + f)
        self.count_box.setVisible(st.running)
        self.stop_btn.setVisible(st.running)
        self.count_label.setText(L(f"{st.finished_count} из {len(st.jobs)}", f"{st.finished_count} of {len(st.jobs)}"))
        self.save_folder_btn.setVisible(not st.running)
        self.save_all_btn.setVisible(not st.running)
        en = has and ready
        self.save_folder_btn.setEnabled(en)
        self.save_all_btn.setEnabled(en)
        self.act_save_all.setEnabled(en)
        self.act_save_folder.setEnabled(en)
        self.act_stop.setEnabled(st.running)
        self.act_demo.setEnabled(ready)
        self.overall.setVisible(st.running)
        self.overall.set(st.overall_progress)

    def engine_changed(self):
        self.overlay.refresh()
        self.inspector.refresh_demo()
        for r in self.rows.values():
            r.refresh()
        self.refresh_bottom()

    def done_sound(self):
        if sys.platform == "win32":
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)

    # ------------------------------------------------------------ files
    def open_files(self):
        exts = " ".join(f"*.{e}" for e in sorted(AUDIO_EXT))
        paths, _ = QFileDialog.getOpenFileNames(self, L("Выберите песни (можно несколько)", "Choose songs (several are fine)"),
                                                "", f"{L('Аудио и видео', 'Audio and video')} ({exts});;{L('Все файлы', 'All files')} (*)")
        if paths:
            self.studio.add(paths)

    def choose_folder(self, action):
        d = QFileDialog.getExistingDirectory(self, L("Сохранить сюда", "Save here"), self.studio.settings.outputFolder or "")
        if d:
            self.studio.settings.outputFolder = os.path.normpath(d)
            self.studio.settings_changed()
            self.refresh_bottom()
            action(os.path.normpath(d))

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.drop.set_targeted(True)

    def dragLeaveEvent(self, _e):
        self.drop.set_targeted(False)

    def dropEvent(self, e):
        self.drop.set_targeted(False)
        self.studio.add([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if getattr(self, "overlay", None):
            self.overlay.setGeometry(self.centralWidget().rect())

    def closeEvent(self, e):
        self.studio.stop()
        self.studio.player.stop()
        super().closeEvent(e)


def run():
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mnsgermany.ClickStudio")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("Click Studio")
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    w = MainWindow()
    w.show()
    return app.exec()
