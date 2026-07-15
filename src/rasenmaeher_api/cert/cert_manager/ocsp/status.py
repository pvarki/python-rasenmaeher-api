"""Serial number -> certificate status lookup against the DB."""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from cryptography import x509
from cryptography.x509 import ocsp
from sqlmodel import select

from rasenmaeher_api.cert.cert_manager.private import validate_reason
from rasenmaeher_api.db.engine import EngineWrapper
from rasenmaeher_api.db.issuedcerts import IssuedCert
from rasenmaeher_api.db.people import Person
from rasenmaeher_api.rmsettings import RMSettings

LOGGER = logging.getLogger(__name__)


@dataclass
class CertStatusResult:
    """Verdict for a single serial"""

    status: ocsp.OCSPCertStatus
    revocation_time: Optional[datetime] = None  # required when REVOKED
    revocation_reason: Optional[x509.ReasonFlags] = None


async def lookup_status(serial: int) -> CertStatusResult:
    """Resolve a cert serial to good/revoked/unknown using Person and issued_certs records"""
    with EngineWrapper.get_session() as session:
        person = session.exec(select(Person).where(Person.cert_serial == str(serial))).first()

    if person:
        if person.deleted is None:
            return CertStatusResult(status=ocsp.OCSPCertStatus.GOOD)
        else:
            return CertStatusResult(
                status=ocsp.OCSPCertStatus.REVOKED,
                revocation_time=person.deleted,
                revocation_reason=validate_reason(person.revoke_reason or "unspecified"),
            )

    if issued_cert := await IssuedCert.by_serial(str(serial)):
        settings = RMSettings.singleton()
        if issued_cert.cn == settings.mtls_client_cert_cn:
            return CertStatusResult(status=ocsp.OCSPCertStatus.GOOD)
        try:
            if issued_cert.cn in settings.valid_product_cns:
                return CertStatusResult(status=ocsp.OCSPCertStatus.GOOD)
        except Exception:
            LOGGER.debug("valid_product_cns lookup failed", exc_info=True)
        return CertStatusResult(
            status=ocsp.OCSPCertStatus.REVOKED,
            revocation_time=issued_cert.updated,
            revocation_reason=x509.ReasonFlags.cessation_of_operation,
        )

    return CertStatusResult(status=ocsp.OCSPCertStatus.UNKNOWN)
