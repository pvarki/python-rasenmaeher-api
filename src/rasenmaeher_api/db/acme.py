"""Persist ACME accounts, replay nonces, and the single order on each approved enrollment."""

import datetime
import hashlib
import logging
import secrets
import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, col, delete, select
from sqlmodel.sql.expression import SelectOfScalar

from ..cert.acme import ACMEError, validate_device_csr
from .engine import EngineWrapper
from .enrollments import ACME_CLIENT_IDENTIFIER_KEY, ACME_ORDER_KEY, Enrollment, EnrollmentState
from .errors import BackendError, CallsignReserved
from .nonces import SeenToken
from .people import Person

LOGGER = logging.getLogger(__name__)
NONCE_LIFETIME = datetime.timedelta(minutes=10)
NONCE_PREFIX = "acme-nonce:"
ACCOUNT_PREFIX = "acme-account:"


def issue_nonce(prune: bool = False) -> str:
    """Mint a short-lived nonce shared by every API worker."""
    now = datetime.datetime.now(datetime.UTC)
    nonce = f"{int(now.timestamp()):010d}-{secrets.token_urlsafe(24)}"
    with EngineWrapper.get_session() as session:
        if prune:
            cutoff = int((now - NONCE_LIFETIME).timestamp())
            token = col(SeenToken.token)
            session.exec(delete(SeenToken).where(token >= NONCE_PREFIX, token < f"{NONCE_PREFIX}{cutoff:010d}-"))
        session.add(SeenToken(token=f"{NONCE_PREFIX}{nonce}"))
        session.commit()
    return nonce


def consume_nonce(nonce: str) -> None:
    """Remove an unexpired nonce atomically, allowing its use just once."""
    cutoff = datetime.datetime.now(datetime.UTC) - NONCE_LIFETIME
    with EngineWrapper.get_session() as session:
        used = session.exec(
            delete(SeenToken)
            .where(col(SeenToken.token) == f"{NONCE_PREFIX}{nonce}", col(SeenToken.created) > cutoff)
            .returning(col(SeenToken.pk))
        ).first()
        session.commit()
    if used is None:
        raise ACMEError("badNonce", "Unknown, expired, or already used nonce")


def account_exists(account: str) -> bool:
    """Check whether a public account key was registered."""
    with EngineWrapper.get_session() as session:
        return (
            session.exec(select(SeenToken.pk).where(SeenToken.token == f"{ACCOUNT_PREFIX}{account}")).first()
            is not None
        )


def register_account(account: str) -> bool:
    """Register the public key once across concurrent requests."""
    with EngineWrapper.get_session() as session:
        created = session.exec(
            insert(SeenToken)
            .values(pk=uuid.uuid4(), token=f"{ACCOUNT_PREFIX}{account}", auditmeta={})
            .on_conflict_do_nothing(index_elements=[col(SeenToken.token)])
            .returning(col(SeenToken.pk))
        ).first()
        session.commit()
    return created is not None


def order_data(enrollment: Enrollment) -> dict[str, Any]:
    """Read ACME's metadata from the enrollment that owns the order."""
    data = enrollment.extra.get(ACME_ORDER_KEY)
    return data if isinstance(data, dict) else {}


def _locked(session: Session, query: SelectOfScalar[Enrollment]) -> Enrollment | None:
    # A concurrent finalization can hold the row while awaiting the signer.
    # NOWAIT keeps a synchronous database call from blocking the event loop.
    try:
        return session.exec(query.with_for_update(nowait=True)).first()
    except OperationalError as exc:
        if getattr(exc.orig, "pgcode", None) != "55P03":  # lock_not_available
            raise
        raise ACMEError("serverInternal", "Order is being updated. Retry shortly.", 503) from exc


def _check_approval(enrollment: Enrollment) -> None:
    expires_at = enrollment.acme_authorization_expires_at
    if enrollment.deleted is not None or expires_at is None or datetime.datetime.now(datetime.UTC) >= expires_at:
        raise ACMEError("unauthorized", "Enrollment is no longer authorized for ACME issuance", 403)


def _check_order(enrollment: Enrollment | None, account: str) -> Enrollment:
    if enrollment is None or order_data(enrollment).get("account") != account:
        raise ACMEError("unauthorized", "Order is unavailable to this account", 403)
    if enrollment.state != EnrollmentState.APPROVED or enrollment.person is None or enrollment.deleted is not None:
        _check_approval(enrollment)
    return enrollment


def new_order(identifier: str, account: str) -> Enrollment:
    """Consume the enrollment identifier by binding it to exactly one account and order."""
    with EngineWrapper.get_session() as session:
        enrollment = _locked(
            session,
            select(Enrollment).where(col(Enrollment.extra)[ACME_CLIENT_IDENTIFIER_KEY].as_string() == identifier),
        )
        if enrollment is None:
            raise ACMEError("rejectedIdentifier", "Identifier does not belong to an approved enrollment")
        if order_data(enrollment):
            return _check_order(enrollment, account)
        _check_approval(enrollment)
        enrollment.extra = {
            **enrollment.extra,
            ACME_ORDER_KEY: {"account": account, "token": secrets.token_urlsafe(32)},
        }
        session.add(enrollment)
        session.commit()
        session.refresh(enrollment)
        return enrollment


def list_orders(account: str) -> list[uuid.UUID]:
    """List order IDs bound to this account."""
    with EngineWrapper.get_session() as session:
        return list(
            session.exec(
                select(Enrollment.pk).where(col(Enrollment.extra)[ACME_ORDER_KEY]["account"].as_string() == account)
            )
        )


def get_order(order_id: uuid.UUID, account: str) -> Enrollment:
    """Read an order for its owning account."""
    with EngineWrapper.get_session() as session:
        return _check_order(session.get(Enrollment, order_id), account)


def accept_challenge(order_id: uuid.UUID, account: str) -> Enrollment:
    """Record the bound account's acknowledgment in the enrollment-token pilot."""
    with EngineWrapper.get_session() as session:
        enrollment = _check_order(_locked(session, select(Enrollment).where(Enrollment.pk == order_id)), account)
        data = order_data(enrollment)
        if "validated" not in data:
            data = {**data, "validated": datetime.datetime.now(datetime.UTC).isoformat()}
            enrollment.extra = {**enrollment.extra, ACME_ORDER_KEY: data}
            session.add(enrollment)
            session.commit()
            session.refresh(enrollment)
        return enrollment


async def finalize_order(order_id: uuid.UUID, account: str, csr_der: bytes) -> Enrollment:
    """Pin the CSR before calling the signer and commit the certificate with its enrollment."""
    digest = hashlib.sha256(csr_der).hexdigest()
    query = select(Enrollment).where(Enrollment.pk == order_id)
    with EngineWrapper.get_session() as session:
        enrollment = _check_order(_locked(session, query), account)
        data = order_data(enrollment)
        if "validated" not in data:
            raise ACMEError("orderNotReady", "Complete the challenge before finalizing", 403)
        if data.get("csr_digest", digest) != digest:
            raise ACMEError("badCSR", "A different CSR was already submitted to this order")
        if enrollment.person is not None:
            return enrollment
        csr_pem = validate_device_csr(csr_der, enrollment.callsign, enrollment.acme_client_identifier or "")
        if "csr_digest" not in data:
            enrollment.extra = {**enrollment.extra, ACME_ORDER_KEY: {**data, "csr_digest": digest}}
            session.add(enrollment)
            session.commit()

    with EngineWrapper.get_session() as session:
        enrollment = _check_order(_locked(session, query), account)
        if enrollment.person is not None:
            return enrollment
        person_extra = {
            key: value
            for key, value in enrollment.extra.items()
            if key not in (ACME_ORDER_KEY, ACME_CLIENT_IDENTIFIER_KEY)
        }
        try:
            async with Person.issue_cert(session, enrollment.callsign, person_extra, csr_pem) as person:
                enrollment.csr = csr_pem
                enrollment.person = person.pk
                enrollment.state = EnrollmentState.APPROVED
                session.add(enrollment)
                session.commit()
        except CallsignReserved as exc:
            raise ACMEError("unauthorized", "Callsign is already in use", 403) from exc
        except BackendError as exc:
            raise ACMEError("serverInternal", "The certificate signer could not complete issuance", 503) from exc
        session.refresh(enrollment)
        session.refresh(person)
    try:
        await person.complete_provisioning()
    except Exception:
        LOGGER.exception("Post-issuance provisioning failed for ACME enrollment %s", order_id)
    return enrollment
