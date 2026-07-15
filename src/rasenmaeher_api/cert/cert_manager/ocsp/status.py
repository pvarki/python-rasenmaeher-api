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
        try:
            product_cns = settings.valid_product_cns
        except Exception:
            LOGGER.debug("valid_product_cns lookup failed", exc_info=True)
            product_cns = []
        # Product/service infra certs are trusted by CA membership
        if issued_cert.cn == settings.mtls_client_cert_cn or issued_cert.cn in product_cns:
            return CertStatusResult(status=ocsp.OCSPCertStatus.GOOD)
        # Otherwise it's a per-user cert signed via the product path (e.g. TAK's
        # per-callsign client cert). Honor the owning Person's revocation.
        with EngineWrapper.get_session() as session:
            owner = session.exec(select(Person).where(Person.callsign == issued_cert.cn)).first()
        if owner and owner.deleted is not None:
            return CertStatusResult(
                status=ocsp.OCSPCertStatus.REVOKED,
                revocation_time=owner.deleted,
                revocation_reason=validate_reason(owner.revoke_reason or "unspecified"),
            )
        return CertStatusResult(status=ocsp.OCSPCertStatus.GOOD)

    return CertStatusResult(status=ocsp.OCSPCertStatus.UNKNOWN)
