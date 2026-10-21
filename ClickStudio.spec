# PyInstaller: "Click Studio.exe" (window) and click_engine.exe (analysis, Python + madmom) in one folder.
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

block_cipher = None
icon = "resources/AppIcon.ico"
qt_unused = ["PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf", "PySide6.QtSql",
             "PySide6.QtOpenGL", "PySide6.QtSvg", "PySide6.QtDBus", "PySide6.QtConcurrent", "PySide6.QtTest", "PySide6.QtXml"]

app = Analysis(["app/main.py"], pathex=["app"],
               datas=[("resources/AppIcon-1024.png", "resources"), ("resources/AppIcon.ico", "resources")],
               hiddenimports=["license", "studio", "ui"],
               excludes=["tkinter", "madmom", "scipy", "matplotlib", "av"] + qt_unused)

engine_datas = collect_data_files("madmom") + collect_data_files("av")
for pkg in ("madmom", "numpy", "scipy", "soundfile", "av"):
    try:
        engine_datas += copy_metadata(pkg)
    except Exception:
        pass
engine = Analysis(["engine/click_engine.py"], pathex=["engine"],
                  datas=engine_datas,
                  binaries=collect_dynamic_libs("soundfile") + collect_dynamic_libs("av"),
                  # madmom's model pickles name numpy.core.* (numpy 2 keeps it as a shim the analysis does not see)
                  hiddenimports=collect_submodules("madmom") + collect_submodules("av") + collect_submodules("numpy.core")
                  + ["soundfile", "scipy.signal",
                                                                                        "scipy.ndimage"],
                  excludes=["tkinter", "PySide6", "matplotlib", "IPython", "pytest"])

utf8 = [("X utf8_mode=1", None, "OPTION")]  # JSON lines with Cyrillic paths stay UTF-8 through the pipe
app_exe = EXE(PYZ(app.pure), app.scripts, utf8, exclude_binaries=True, name="Click Studio", icon=icon,
              console=False, upx=False, version=None)
engine_exe = EXE(PYZ(engine.pure), engine.scripts, utf8, exclude_binaries=True, name="click_engine", icon=icon,
                 console=True, upx=False)

COLLECT(app_exe, app.binaries, app.datas, engine_exe, engine.binaries, engine.datas,
        name="Click Studio", upx=False)
