"""Click Studio for Windows. Service flags: --machine-code, --check-license email key [code]."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    import license as lic
    if sys.stdout is None and any(a in sys.argv for a in ("--machine-code", "--check-license")):
        import io
        sys.stdout = io.StringIO()  # windowed exe started without a console: show the answer in a box
        code = lic.cli(sys.argv[1:])
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, sys.stdout.getvalue(), "Click Studio", 0)
        return code
    code = lic.cli(sys.argv[1:])
    if code is not None:
        return code
    import ui
    return ui.run()


if __name__ == "__main__":
    sys.exit(main())
