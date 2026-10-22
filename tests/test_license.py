"""Licence checks from the activation doc (section 9). Signs with a throwaway test key, never the real one."""
import base64, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
import license as lic  # noqa: E402

from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import padding, rsa  # noqa: E402

real_key = lic.PUBLIC_KEY
serialization.load_der_public_key(base64.b64decode(real_key))  # the embedded key parses

priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
lic.PUBLIC_KEY = base64.b64encode(priv.public_key().public_bytes(
    serialization.Encoding.DER, serialization.PublicFormat.PKCS1)).decode()


def sign(msg):
    return base64.b64encode(priv.sign(msg.encode(), padding.PKCS1v15(), hashes.SHA256())).decode()


code = lic.machine_code("uuid:4C4C4544-0042-3610-8051-B4C04F4A3933")
assert len(code) == 16 and code == code.upper()
# same formula as the Mac version: sha256("clickstudio|uuid:<UUID>")[:16]
import hashlib  # noqa: E402
assert code == hashlib.sha256(b"clickstudio|uuid:4C4C4544-0042-3610-8051-B4C04F4A3933").hexdigest()[:16].upper()
key = sign(f"ClickStudio-1|buyer@example.com|{code}")
assert len(key) == 344

assert lic.valid("buyer@example.com", key, code)
assert lic.valid("  Buyer@Example.COM ", key, lic.pretty(code).lower())
assert lic.valid("buyer@example.com", key[:100] + "\n" + key[100:], code)
assert not lic.valid("other@example.com", key, code)
assert not lic.valid("buyer@example.com", key, lic.machine_code("uuid:00000000-1111-2222-3333-444444444444"))
assert not lic.valid("buyer@example.com", sign(f"CueDeck-1|buyer@example.com|{code}"), code)
assert not lic.valid("buyer@example.com", sign(f"QLabWaveform-2|buyer@example.com|{code}"), code)
assert not lic.valid("buyer@example.com", "garbage!!", code)
assert not lic.valid("buyer@example.com", "", code)
assert not lic.valid("", key, code)

assert lic._real_uuid("FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF") == ""
assert lic._real_uuid("00000000-0000-0000-0000-000000000000") == ""
assert lic._real_uuid("4c4c4544-0042-3610-8051-b4c04f4a3933\r\n") == "4C4C4544-0042-3610-8051-B4C04F4A3933"
assert lic.request_text(code) == f"Click Studio activation request\nClickStudio-1|{code}\n"

with tempfile.TemporaryDirectory() as d:
    os.environ["APPDATA"] = d
    lic.save(" Buyer@Example.com ", key)
    assert lic.load() == ("buyer@example.com", key)
    # trial: 3 clicks per computer, kept on disk (and in HKCU on Windows)
    lic.REG_KEY = r"Software\Click Studio Test"
    lic.set_trial_used(0)
    assert lic.trial_left() == 3
    lic.set_trial_used(2)
    assert lic.trial_used() == 2 and lic.trial_left() == 1
    if sys.platform == "win32":
        os.remove(os.path.join(d, "Click Studio", "trial.json"))
        assert lic.trial_used() == 2, "deleting the settings folder must not reset the trial"
        import winreg
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, lic.REG_KEY)

# CLI against the real embedded key: a test signature must be rejected
lic.PUBLIC_KEY = real_key
assert not lic.valid("buyer@example.com", key, code)
main = os.path.join(os.path.dirname(__file__), "..", "app", "license.py")
r = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {os.path.dirname(main)!r}); import license; "
                    f"sys.exit(license.cli(['--check-license', 'buyer@example.com', {key!r}, {code!r}]))"])
assert r.returncode == 1
print("licence tests passed")
