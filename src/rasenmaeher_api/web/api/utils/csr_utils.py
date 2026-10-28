"""Utils for checking CSR:s etc"""

import logging
import secrets

from cryptography import x509
from cryptography.x509.oid import NameOID
from libadvian.binpackers import ensure_utf8

LOGGER = logging.getLogger(__name__)


# FIXME: This should be part of libpvarki


def verify_csr(csrpem: str, callsign: str) -> bool:
    """Verify CSR matches our rules for CN/DN for the given callsign

    Two properties are checked, and both are load-bearing:

    1. The CSR is signed by the key it carries. Without this we have no proof that whoever
       submitted the request holds the private key, and a request we cannot vouch for would be
       passed to the CA anyway -- which answers with an error *after* the Person row has been
       committed, permanently spending the callsign.
    2. The subject carries exactly one CN and it equals the callsign. This used to be a substring
       test on the rendered RFC4514 string, which accepted a great deal more than it looks like:
       ``CN=OTTER1X`` matched callsign ``OTTER1``, and ``OU=CN=OTTER1,CN=ADMIN`` matched it too
       while the certificate the CA then issued carried ``CN=ADMIN``. The mTLS edge authorises on
       the CN it reads from the certificate, so that is an identity mismatch, not a cosmetic one.

    Attributes other than CN are left alone on purpose: an MDM filling the subject template of a
    device may add O, OU or ST, nothing downstream reads them, and refusing them would break
    enrolment for no gain.
    """
    csr = x509.load_pem_x509_csr(ensure_utf8(csrpem))
    if not csr.is_signature_valid:
        LOGGER.warning(f"CSR signature does not verify. callsign={callsign}")
        return False
    common_names = [attr.value for attr in csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)]
    LOGGER.debug(f"CNs={common_names} callsign={callsign}")
    if common_names != [callsign]:
        LOGGER.warning(f"Callsign does not match CSR subject. CNs={common_names} callsign={callsign}")
        return False
    # TODO: check that keyusages in the CSR are fine
    #       crypto.X509Extension(b"keyUsage", True, b"digitalSignature,nonRepudiation,keyEncipherment"),
    #       crypto.X509Extension(b"extendedKeyUsage", True, b"clientAuth"),
    return True


def csr_carries_enrolment_proof(csrpem: str, callsign: str, approvecode: str) -> bool:
    """Does this request carry the per-enrolment code, proving the MDM assigned this device

    The public SCEP endpoint is reachable by anyone, and the SCEP challenge is not a secret: it
    sits in the MDM's configuration and travels in every device's request. So without this the
    last gate is a callsign, which is a short human-chosen string an attacker can guess.

    The MDM carries the proof by putting ``<callsign>@<approvecode>`` in the one per-host field it
    can substitute into a subject, rendered into an attribute beside the common name. Which
    attribute it renders into is the MDM's business and not something to hard-code, but exactly
    one attribute may carry an "@": otherwise one request could hold a guess per attribute and
    test hundreds of codes at once.
    """
    wanted = f"{callsign}@{approvecode}"
    if not approvecode or not wanted.isascii():
        return False
    try:
        csr = x509.load_pem_x509_csr(ensure_utf8(csrpem))
    except ValueError:
        return False
    carriers = [
        attribute.value
        for attribute in csr.subject
        if attribute.oid != NameOID.COMMON_NAME and isinstance(attribute.value, str) and "@" in attribute.value
    ]
    if len(carriers) != 1 or not carriers[0].isascii():
        # compare_digest raises on non-ascii str, and nothing we issue for is non-ascii
        return False
    return secrets.compare_digest(carriers[0], wanted)
