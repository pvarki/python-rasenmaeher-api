"""The people list: when each person's certificate ends"""

import datetime
import secrets
import uuid
from pathlib import Path

import cryptography.x509
import pytest
from async_asgi_testclient import TestClient  # type: ignore[import-untyped]

from rasenmaeher_api.db import Person


def test_no_certificate_file_means_no_end(tmp_path: Path) -> None:
    """A person whose certificate cannot be read is still listed"""
    person = Person(pk=uuid.uuid4(), callsign="NOCERT1", certspath=str(tmp_path))

    assert person.cert_ends() is None


def test_a_file_that_is_no_certificate_means_no_end(tmp_path: Path) -> None:
    person = Person(pk=uuid.uuid4(), callsign="BADCERT1", certspath=str(tmp_path))
    person.certfile.write_text("-----BEGIN CERTIFICATE-----\nnot one\n-----END CERTIFICATE-----\n", encoding="utf-8")

    assert person.cert_ends() is None


def test_a_date_no_calendar_has_means_no_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The date is read inside the same guard as the file: a certificate with such a date raises only then"""

    class OddDates:
        @property
        def not_valid_after_utc(self) -> datetime.datetime:
            raise ValueError("year 0 is out of range")

    monkeypatch.setattr(cryptography.x509, "load_pem_x509_certificate", lambda _data: OddDates())
    person = Person(pk=uuid.uuid4(), callsign="ODDCERT1", certspath=str(tmp_path))
    person.certfile.write_text("anything", encoding="utf-8")

    assert person.cert_ends() is None


@pytest.mark.asyncio(loop_scope="session")
async def test_the_list_says_when_each_certificate_ends(dbinit_func: None, user_mtls_admin_client: TestClient) -> None:
    """An admin sees the end of every certificate, exactly as the certificate states it"""
    _ = dbinit_func
    callsign = f"CERTENDS{secrets.token_hex(3)}"
    person = await Person.create_with_cert(callsign)
    leaf = cryptography.x509.load_pem_x509_certificate(person.certfile.read_bytes())

    resp = await user_mtls_admin_client.get("/api/v1/people/list")
    resp.raise_for_status()

    [listed] = [each for each in resp.json()["callsign_list"] if each["callsign"] == callsign]
    assert listed["cert_ends"] == leaf.not_valid_after_utc.isoformat()
    assert datetime.datetime.fromisoformat(listed["cert_ends"]) > datetime.datetime.now(datetime.UTC)
    assert person.cert_ends() == leaf.not_valid_after_utc
