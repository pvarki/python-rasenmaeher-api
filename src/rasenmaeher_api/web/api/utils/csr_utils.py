"""Utils for checking CSR:s etc"""

import logging

from cryptography import x509
from cryptography.x509.oid import NameOID
from libadvian.binpackers import ensure_utf8

from ....cert.usages import disallowed_usages

LOGGER = logging.getLogger(__name__)


# FIXME: This should be part of libpvarki


def verify_csr(csrpem: str, callsign: str) -> bool:
    """Verify CSR matches our rules for CN/DN and key usages for the given callsign"""
    csr = x509.load_pem_x509_csr(ensure_utf8(csrpem))
    dn = csr.subject.rfc4514_string()
    LOGGER.debug(f"DN={dn} callsign={callsign}")
    cns = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if len(csr.subject) != 1 or len(cns) != 1 or cns[0].value != callsign:
        LOGGER.warning(f"Callsign does not match CSR subject. DN={dn} callsign={callsign}")
        return False
    try:
        extra = disallowed_usages(csrpem, callsign)
    except ValueError as exc:
        LOGGER.warning(f"CSR usages could not be checked. error={exc} callsign={callsign}")
        return False
    if extra:
        LOGGER.warning(f"CSR requests usages not allowed for callsign. usages={sorted(extra)} callsign={callsign}")
        return False
    return True
