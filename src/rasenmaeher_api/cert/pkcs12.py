"""PKCS12 containers that rasenmaeher builds itself

libpvarki.mtlshelp.pkcs12 covers the passworded case. This is the one thing it cannot do, and
the eventual home for it is probably there rather than here, since takrmapi builds containers too.
"""

import logging
import subprocess  # nosec
from pathlib import Path

LOGGER = logging.getLogger(__name__)
# Same algorithms libpvarki.mtlshelp.pkcs12.serialize_legacy_pkcs12 uses, for the same broad client
# support. They are also the documented recipe for Windows, so do not "modernise" them to AES
# without testing Windows and older Android: the empty password means they protect nothing anyway.
NOPASS_PKCS12_ALGOS = ("-keypbe", "PBE-SHA1-3DES", "-certpbe", "PBE-SHA1-3DES", "-macalg", "sha1")


def write_nopass_pkcs12(certfile: Path, keyfile: Path | None, target: Path, friendlyname: str) -> None:
    """Write a PKCS12 container that opens with an empty password

    ponytail: shells out to openssl because pyca/cryptography refuses to serialize with an empty
    password ("Password must be 1 or more bytes"), and its only password-free alternative,
    NoEncryption(), emits a MAC-less container that the JDK PKCS12 provider reads as having no
    entries at all. The container therefore has to stay encrypted, just with an empty password:
    that is precisely what AOSP CredentialHelper.hasPassword() probes for before Android's
    CertInstaller decides whether to show its password dialog.
    """
    # People who enrolled with their own CSR get a cert-only container, there is no key to put in it.
    # -name labels the key, so with no key the friendly name has to go on the cert bag instead.
    keyargs = ["-inkey", str(keyfile)] if keyfile else ["-nokeys"]
    nameargs = ["-name", friendlyname] if keyfile else ["-caname", friendlyname]
    cmd = [
        "openssl",
        "pkcs12",
        "-export",
        "-out",
        str(target),
        *keyargs,
        "-in",
        str(certfile),
        *nameargs,
        *NOPASS_PKCS12_ALGOS,
        "-passout",
        "pass:",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)  # nosec
    except subprocess.CalledProcessError as exc:
        # capture_output swallows the reason, and without it this is an unexplained 500
        LOGGER.error("openssl pkcs12 failed for {}: {}".format(target, exc.stderr.decode("utf-8", errors="replace")))
        raise
    # No password means the key is only as safe as the file mode
    target.chmod(0o600)
