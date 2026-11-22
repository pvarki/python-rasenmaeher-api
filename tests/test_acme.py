"""Exercise the Apple ACME flow through the public API and the configured CA."""

import datetime
import json
import plistlib
import secrets
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest
from async_asgi_testclient import TestClient  # type: ignore[import-untyped]
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.x509.oid import ExtendedKeyUsageOID
from fastapi import FastAPI

from rasenmaeher_api.cert.acme import b64url
from rasenmaeher_api.cert.backend import sign_csr
from rasenmaeher_api.cert.errors import CertError
from rasenmaeher_api.db import EngineWrapper, Enrollment, EnrollmentState, Person
from rasenmaeher_api.db import people as people_db
from rasenmaeher_api.db.enrollments import ACME_AUTHORIZATION_LIFETIME
from rasenmaeher_api.db.errors import NotFound

ORIGIN = "https://localmaeher.dev.pvarki.fi"


class ACMEClient:
    """Generate the same ES256 flattened JWS requests used by the Apple client."""

    def __init__(self, client: httpx.AsyncClient, directory: dict[str, str], nonce: str) -> None:
        self.client = client
        self.directory = directory
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.nonce = nonce
        self.account: str | None = None

    async def send(
        self,
        url: str,
        payload: dict[str, Any] | None = None,
        *,
        nonce: str | None = None,
        signed_url: str | None = None,
    ) -> httpx.Response:
        protected = {"alg": "ES256", "url": signed_url or url, "nonce": nonce or self.nonce}
        public = self.key.public_key().public_numbers()
        identity = (
            {"kid": self.account}
            if self.account and url != self.directory["newAccount"]
            else {
                "jwk": {
                    "kty": "EC",
                    "crv": "P-256",
                    "x": b64url(public.x.to_bytes(32)),
                    "y": b64url(public.y.to_bytes(32)),
                }
            }
        )
        encoded_header = b64url(json.dumps({**protected, **identity}).encode())
        encoded_payload = b64url(json.dumps(payload).encode()) if payload is not None else ""
        signature = self.key.sign(f"{encoded_header}.{encoded_payload}".encode(), ec.ECDSA(hashes.SHA256()))
        r, s = utils.decode_dss_signature(signature)
        response = await self.client.post(
            urlsplit(url).path,
            json={
                "protected": encoded_header,
                "payload": encoded_payload,
                "signature": b64url(r.to_bytes(32) + s.to_bytes(32)),
            },
            headers={"Content-Type": "application/jose+json"},
        )
        self.nonce = response.headers["Replay-Nonce"]
        return response

    async def register(self) -> httpx.Response:
        response = await self.send(self.directory["newAccount"], {"termsOfServiceAgreed": True})
        response.raise_for_status()
        self.account = response.headers["Location"]
        return response


def csr(callsign: str, key: ec.EllipticCurvePrivateKey, san: x509.GeneralName | None = None) -> dict[str, str]:
    """Build the profile's device CSR with an optional alternate name."""
    builder = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, callsign)]))
        .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
    )
    if san is not None:
        builder = builder.add_extension(x509.SubjectAlternativeName([san]), critical=False)
    return {"csr": b64url(builder.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.DER))}


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("dbinit_sess")
@pytest.mark.parametrize("app_instance", ["RSA"], indirect=True)
async def test_apple_acme_issuance(
    app_instance: FastAPI, tilauspalvelu_jwt_admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Issue once for the approved profile and recover from a signer failure with the same CSR."""
    admin = tilauspalvelu_jwt_admin_client
    invite = await admin.post("/api/v1/enrollment/invitecode/create")
    invite.raise_for_status()
    invite_code = invite.json()["invite_code"]
    callsign = f"acme{secrets.token_hex(4)}"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_instance), base_url=ORIGIN) as client:
        directory_response = await client.get("/api/v1/acme/directory", headers={"Host": "other.example.test"})
        directory_response.raise_for_status()
        directory = directory_response.json()
        assert directory["newOrder"] == f"{ORIGIN}/api/v1/acme/new-order"
        nonce_response = await client.head(urlsplit(directory["newNonce"]).path)
        assert nonce_response.status_code == 200
        assert nonce_response.content == b""
        nonce = nonce_response.headers["Replay-Nonce"]
        apple = ACMEClient(client, directory, nonce)
        registered = await apple.register()
        assert registered.status_code == 201
        assert apple.account is not None
        assert (await apple.send(apple.account)).json() == registered.json()
        replay = await apple.send(directory["newOrder"], {"identifiers": []}, nonce=nonce)
        assert replay.status_code == 400
        assert replay.json()["type"].endswith(":badNonce")
        mismatched = await apple.send(directory["newOrder"], {}, signed_url=directory["newAccount"])
        assert mismatched.status_code == 400
        second_nonce = await client.get(urlsplit(directory["newNonce"]).path)
        assert second_nonce.status_code == 204
        other = ACMEClient(client, directory, second_nonce.headers["Replay-Nonce"])
        assert (await other.register()).status_code == 201
        second_account = other.account
        other.account = apple.account
        assert (await other.send(apple.account)).json()["type"].endswith(":unauthorized")
        other.account = second_account
        assert (await other.send(apple.account)).status_code == 403

        invited = await client.post(
            "/api/v1/enrollment/invitecode/enroll",
            json={"invite_code": invite_code, "callsign": callsign, "acme": True},
        )
        invited.raise_for_status()
        auth = {"Authorization": f"Bearer {invited.json()['jwt']}"}
        approval = {"callsign": callsign, "approvecode": invited.json()["approvecode"]}
        record = await Enrollment.by_callsign(callsign)
        identifier = {"identifiers": [{"type": "permanent-identifier", "value": record.acme_client_identifier}]}
        assert (await apple.send(directory["newOrder"], identifier)).status_code == 403
        (await admin.post("/api/v1/enrollment/accept", json=approval)).raise_for_status()
        profile = await client.get("/api/v1/enrollment/acme-profile", headers=auth)
        profile.raise_for_status()
        identity = plistlib.loads(profile.content)["PayloadContent"][0]
        assert identity["DirectoryURL"] == f"{ORIGIN}/api/v1/acme/directory"
        assert identity["ClientIdentifier"] == record.acme_client_identifier
        assert identity["Attest"] is False

        order = await apple.send(directory["newOrder"], identifier)
        assert order.status_code == 201
        assert order.json()["status"] == "pending"
        order_url = order.headers["Location"]
        finalize = order.json()["finalize"]
        assert (await apple.send(registered.json()["orders"])).json() == {"orders": [order_url]}
        assert (await apple.send(directory["newOrder"], identifier)).headers["Location"] == order_url
        assert (await other.send(directory["newOrder"], identifier)).status_code == 403
        assert (await other.send(order_url)).status_code == 403

        device_key = ec.generate_private_key(ec.SECP256R1())
        request = csr(callsign, device_key)
        assert (await apple.send(finalize, request)).json()["type"].endswith(":orderNotReady")
        authorization = await apple.send(order.json()["authorizations"][0])
        assert authorization.json()["status"] == "pending"
        challenge = authorization.json()["challenges"][0]
        assert challenge["type"] == "device-attest-01"
        assert (await apple.send(challenge["url"])).json() == challenge
        assert (await apple.send(challenge["url"], {})).json()["status"] == "valid"
        assert (await apple.send(order_url)).json()["status"] == "ready"
        assert (await apple.send(finalize, csr("differentcallsign", device_key))).json()["type"].endswith(":badCSR")
        assert (await apple.send(finalize, csr(callsign, device_key, x509.DNSName("other.example")))).status_code == 400

        signing_calls = 0

        async def fail_once(pem: str) -> str:
            nonlocal signing_calls
            signing_calls += 1
            if signing_calls == 1:
                raise CertError("Signer temporarily unavailable")
            return await sign_csr(pem)

        monkeypatch.setattr(people_db, "sign_csr", fail_once)
        assert (await apple.send(finalize, request)).status_code == 503
        with pytest.raises(NotFound):
            await Person.by_callsign(callsign)
        replacement = csr(callsign, ec.generate_private_key(ec.SECP256R1()))
        assert (await apple.send(finalize, replacement)).status_code == 400
        finalized = await apple.send(finalize, request)
        finalized.raise_for_status()
        assert finalized.json()["status"] == "valid"
        assert (await apple.send(finalize, request)).json() == finalized.json()
        assert signing_calls == 2

        package = await apple.send(finalized.json()["certificate"])
        package.raise_for_status()
        assert package.headers["Content-Type"] == "application/pem-certificate-chain"
        leaf, issuer, *_ = x509.load_pem_x509_certificates(package.content)
        leaf.verify_directly_issued_by(issuer)
        assert leaf.subject == x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, callsign)])
        assert leaf.public_key() == device_key.public_key()
        person = await Person.by_callsign(callsign)
        assert person.cert_serial == str(leaf.serial_number)
        assert not person.privkeyfile.exists()
        assert (await other.send(finalized.json()["certificate"])).status_code == 403
        status = await client.get(f"/api/v1/enrollment/status?callsign={callsign}", headers=auth)
        assert status.json()["status"] == EnrollmentState.APPROVED

        stale = f"acme{secrets.token_hex(4)}"
        expired = await client.post(
            "/api/v1/enrollment/invitecode/enroll", json={"invite_code": invite_code, "callsign": stale, "acme": True}
        )
        expired.raise_for_status()
        (
            await admin.post(
                "/api/v1/enrollment/accept", json={"callsign": stale, "approvecode": expired.json()["approvecode"]}
            )
        ).raise_for_status()
        stale_record = await Enrollment.by_callsign(stale)
        with EngineWrapper.get_session() as session:
            stale_record.decided_on = datetime.datetime.now(datetime.UTC) - ACME_AUTHORIZATION_LIFETIME
            session.add(stale_record)
            session.commit()
            session.refresh(stale_record)
        stale_id = {"identifiers": [{"type": "permanent-identifier", "value": stale_record.acme_client_identifier}]}
        assert (await apple.send(directory["newOrder"], stale_id)).status_code == 403
