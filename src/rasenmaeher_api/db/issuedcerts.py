"""DB abstraction for non-user certs we signed (product/service mTLS), used by the OCSP responder"""

import logging
from typing import Optional

import sqlalchemy
from cryptography import x509
from sqlmodel import Field, select

from .base import ORMBaseModel
from .engine import EngineWrapper

LOGGER = logging.getLogger(__name__)


class IssuedCert(ORMBaseModel, table=True):
    """serial -> CN records for certs with no Person row"""

    __tablename__ = "issued_certs"

    serial: str = Field(nullable=False, index=True, unique=True)
    cn: str = Field(nullable=False, index=True)

    @classmethod
    async def by_serial(cls, serial: str) -> Optional["IssuedCert"]:
        """Get by serial (decimal string), None if not recorded"""
        with EngineWrapper.get_session() as session:
            return session.exec(select(IssuedCert).where(IssuedCert.serial == serial)).first()


async def record_issued_cert(cert_pem: str) -> None:
    """Record the leaf cert's serial and CN, best-effort (never raises)"""
    try:
        leaf = x509.load_pem_x509_certificate(cert_pem.encode())
        serial = str(leaf.serial_number)
        cn = str(leaf.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value)
        with EngineWrapper.get_session() as session:
            session.add(IssuedCert(serial=serial, cn=cn))
            session.commit()
    except sqlalchemy.exc.IntegrityError:
        LOGGER.debug("issued cert already recorded")
    except Exception:
        LOGGER.exception("failed to record issued cert")
