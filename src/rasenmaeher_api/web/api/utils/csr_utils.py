"""Utils for checking CSR:s etc"""

import logging

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
