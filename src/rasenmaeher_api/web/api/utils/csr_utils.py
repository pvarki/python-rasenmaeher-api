"""Utils for checking CSR:s etc"""

from cryptography import x509
from libadvian.binpackers import ensure_utf8

from rasenmaeher_api.web.api.utils.views import LOGGER


# FIXME: This should be part of libpvarki


def verify_csr(csrpem: str, callsign: str) -> bool:
    """Verify CSR matches our rules for CN/DN for the given callsign"""
    csr = x509.load_pem_x509_csr(ensure_utf8(csrpem))
    dn = csr.subject.rfc4514_string()
    LOGGER.debug("DN={} callsign={}".format(dn, callsign))
    if f"CN={callsign}" not in dn:
        LOGGER.warning("Callsign does not match CSR subject. DN={} callsign={}".format(dn, callsign))
        return False
    # TODO: check that keyusages in the CSR are fine
    #       crypto.X509Extension(b"keyUsage", True, b"digitalSignature,nonRepudiation,keyEncipherment"),
    #       crypto.X509Extension(b"extendedKeyUsage", True, b"clientAuth"),
    return True
