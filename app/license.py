"""Hardware-bound licence, compatible with the Mac version and the key bot.

Key = base64 RSA PKCS#1 v1.5 SHA-256 signature of "ClickStudio-1|<email>|<machine code>".
Machine code = first 16 hex of SHA-256("clickstudio|" + raw hardware id), raw id "uuid:…", "guid:…" or "host:…".
"""
import base64, hashlib, json, os, re, socket, subprocess, sys

PREFIX = "ClickStudio-1"
SALT = "clickstudio|"
REQUEST_EXT = ".csreq"
REQUEST_NAME = "ClickStudio-request" + REQUEST_EXT
TRIAL_SECONDS = 5 * 60
BOT_URL = ""  # the sales bot link; the button is hidden while empty
# PKCS#1 DER, base64 (public half of the author's private.pem, same as the Mac version)
PUBLIC_KEY = (
    "MIIBCgKCAQEA1CxhEwaZQvDwFFfXqxIjWfNpMMkqDj1tExPqe+xt24bSSyDdhqSz1wYW/rb/aOyr5jy82y6gXkjuVHWF/ca9gAbl+Obq+Hs7"
    "ndOjCUHof/lS9+x2BSHzFRXUhAnbbv/79ZAn0SrJ/+ek+q3GMIuXdutZfnEcI91PeefUJCmyAXjMp7HTwfhVnIbqs5T6zG/6rAXRc4q/NNgF"
    "rGBPHx/WuRqel6i0NrOEunS+YzmscP99h9pjpGSr8pBGZKo8hKVgcHDG419p9/8WGlr0ObRMhrE54ai2BDZxawhYdbNY/cLsn5TwpENK20G+"
    "kk9eZP/jQq60WxH3RJt89MMSRtXwBQIDAQAB"
)


def _run(args):
    try:
        flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
        r = subprocess.run(args, capture_output=True, text=True, timeout=15, creationflags=flags)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def _real_uuid(s):
    s = s.strip()
    if re.fullmatch(r"[0-9A-Fa-f-]{32,36}", s) and not re.fullmatch(r"[Ff-]+", s) and not re.fullmatch(r"[0-]+", s):
        return s.upper()
    return ""


def hardware_id():
    if sys.platform == "win32":
        uuid = _real_uuid(_run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                                "(Get-CimInstance Win32_ComputerSystemProduct).UUID"]))
        if uuid:
            return "uuid:" + uuid
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                g = str(winreg.QueryValueEx(k, "MachineGuid")[0]).strip()
            if g:
                return "guid:" + g.upper()
        except OSError:
            pass
    elif sys.platform == "darwin":
        m = re.search(r'"IOPlatformUUID" = "([^"]+)"', _run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]))
        if m:
            return "uuid:" + m.group(1).upper()
    return "host:" + socket.gethostname()


def machine_code(raw=None):
    raw = hardware_id() if raw is None else raw
    return hashlib.sha256((SALT + raw).encode()).hexdigest()[:16].upper()


def pretty(code):
    return "-".join(code[i:i + 4] for i in range(0, 16, 4))


def clean_email(email):
    return str(email or "").strip().lower()


def clean_code(code):
    return re.sub(r"[^0-9A-F]", "", str(code or "").upper())


def valid(email, key, code):
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    email, code = clean_email(email), clean_code(code)
    if not email or len(code) != 16:
        return False
    try:
        sig = base64.b64decode(re.sub(r"\s", "", str(key or "")), validate=True)
        pub = serialization.load_der_public_key(base64.b64decode(PUBLIC_KEY))
        pub.verify(sig, f"{PREFIX}|{email}|{code}".encode(), padding.PKCS1v15(), hashes.SHA256())
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def request_text(code):
    return f"Click Studio activation request\n{PREFIX}|{code}\n"


def request_line(code):
    return f"{PREFIX}|{code}"


def data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    d = os.path.join(base, "Click Studio")
    os.makedirs(d, exist_ok=True)
    return d


def license_path():
    return os.path.join(data_dir(), "license.json")


def load():
    try:
        with open(license_path(), encoding="utf-8") as f:
            d = json.load(f)
        return str(d.get("email", "")), str(d.get("key", ""))
    except (OSError, ValueError):
        return "", ""


def save(email, key):
    with open(license_path(), "w", encoding="utf-8") as f:
        json.dump({"email": clean_email(email), "key": re.sub(r"\s", "", key)}, f)


def cli(argv):
    """--machine-code and --check-license email key [code]; returns an exit code, or None if not a licence flag."""
    if "--machine-code" in argv:
        print(pretty(machine_code()))
        return 0
    if "--check-license" in argv:
        rest = argv[argv.index("--check-license") + 1:]
        if len(rest) < 2:
            print("usage: --check-license email key [code]")
            return 2
        ok = valid(rest[0], rest[1], rest[2] if len(rest) > 2 else machine_code())
        print("valid" if ok else "invalid")
        return 0 if ok else 1
    return None
