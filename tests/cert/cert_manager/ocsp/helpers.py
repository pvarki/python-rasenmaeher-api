"""Signing-CA material, factory types and DB row inserters for the OCSP tests.

Plain functions and types, so they live here rather than in conftest.py.
"""

import uuid
from datetime import datetime
from typing import NamedTuple, Protocol

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509 import ocsp

from rasenmaeher_api.db import EngineWrapper, Person
from rasenmaeher_api.db.issuedcerts import IssuedCert
from tests.cert.helpers import CertFactory


class SigningCA(NamedTuple):
    """An EC CA: the cert and key that sign leaves, plus their PEM encodings.

    The PEMs are what the signer reads out of a k8s Secret, so they are carried
    alongside the parsed objects rather than re-encoded at each use.
    """

    cert: x509.Certificate
    key: ec.EllipticCurvePrivateKey
    cert_pem: bytes
    key_pem: bytes


class LeafFactory(Protocol):
    """Issue an additional leaf from either the real or the foreign CA"""

    def __call__(self, common_name: str, foreign: bool = False) -> x509.Certificate: ...


class RequestFactory(Protocol):
    """Build a DER OCSP request for a leaf"""

    def __call__(
        self,
        leaf: x509.Certificate,
        algorithm: hashes.HashAlgorithm | None = None,
        nonce: bytes | None = None,
        foreign: bool = False,
    ) -> bytes: ...


class Responder(Protocol):
    """Run one request through the responder and parse the reply"""

    async def __call__(self, der: bytes) -> ocsp.OCSPResponse: ...


def make_signing_ca(mint_cert: CertFactory, common_name: str) -> SigningCA:
    """Mint a self-signed EC CA and keep both the parsed objects and the PEMs"""
    cert_pem, key = mint_cert(common_name, ca=True)
    return SigningCA(
        cert=x509.load_pem_x509_certificate(cert_pem.encode("utf-8")),
        key=key,
        cert_pem=cert_pem.encode("utf-8"),
        key_pem=key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )


def add_person(
    serial: int | None = None,
    deleted: datetime | None = None,
    revoke_reason: str | None = None,
    tmp: str = "",
    callsign: str | None = None,
) -> Person:
    """Insert a Person row directly (bypasses cert signing)"""
    person = Person(
        callsign=callsign or f"ocsptest_{uuid.uuid4()}",
        certspath=f"{tmp}/ocsptest/{uuid.uuid4()}",
        extra={},
        cert_serial=str(serial) if serial is not None else None,
    )
    if deleted:
        person.deleted = deleted
        person.revoke_reason = revoke_reason or "unspecified"
    with EngineWrapper.get_session() as session:
        session.add(person)
        session.commit()
        session.refresh(person)
    return person


def add_issued(serial: int, common_name: str) -> None:
    """Insert an IssuedCert row directly"""
    with EngineWrapper.get_session() as session:
        session.add(IssuedCert(serial=str(serial), cn=common_name))
        session.commit()
