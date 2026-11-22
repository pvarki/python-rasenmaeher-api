"""RFC 8555 request authentication for the Apple enrollment client."""

import json
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from ....cert.acme import ACMEError, b64url, decode_b64url
from ....db.acme import account_exists, consume_nonce, issue_nonce
from ....rmsettings import RMSettings

ACME_PREFIX = "/api/v1/acme"
MAX_JWS_BYTES = 32 * 1024


def acme_url(path: str) -> str:
    """Build the public URL from trusted deployment DNS."""
    settings = RMSettings.singleton()
    settings.load_manifest()
    dns = settings.kraftwerk_manifest_dict.get("dns")
    if not isinstance(dns, str) or not dns:
        raise ACMEError("serverInternal", "Deployment DNS is missing from the manifest", 503)
    return f"https://{dns}{ACME_PREFIX}/{path}"


class ACMERoute(APIRoute):
    """Return ACME problem documents and a fresh nonce for signed requests."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            try:
                response = await handler(request)
                response.headers["Link"] = f'<{acme_url("directory")}>; rel="index"'
            except ACMEError as exc:
                response = JSONResponse(
                    {"type": f"urn:ietf:params:acme:error:{exc.code}", "detail": str(exc), "status": exc.status},
                    status_code=exc.status,
                    media_type="application/problem+json",
                )
                if exc.status == 503:
                    response.headers["Retry-After"] = "1"
            response.headers["Cache-Control"] = "no-store"
            if request.method == "POST":
                response.headers["Replay-Nonce"] = issue_nonce()
            return response

        return handle


@dataclass(frozen=True)
class SignedRequest:
    """The verified account ID and JSON payload, or an empty POST-as-GET."""

    account: str
    payload: dict[str, Any] | None

    def json(self) -> dict[str, Any]:
        """Require a JSON object for an operation that changes state."""
        if self.payload is None:
            raise ACMEError("malformed", "Expected a JSON payload")
        return self.payload

    def require_post_as_get(self) -> None:
        """Require an empty payload for reading a private ACME resource."""
        if self.payload is not None:
            raise ACMEError("malformed", "Expected an empty POST-as-GET payload")


def _json_object(encoded: bytes) -> dict[str, Any]:
    parsed = json.loads(encoded)
    if not isinstance(parsed, dict):
        raise TypeError("Expected object")
    return parsed


def _key_from_jwk(jwk: Any) -> ec.EllipticCurvePublicKey:
    if not isinstance(jwk, dict) or jwk.get("kty") != "EC" or jwk.get("crv") != "P-256" or "d" in jwk:
        raise ACMEError("badPublicKey", "Expected a public P-256 JWK")
    x, y = decode_b64url(jwk["x"]), decode_b64url(jwk["y"])
    if len(x) != 32 or len(y) != 32:
        raise ACMEError("badPublicKey", "Expected a public P-256 JWK")
    return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), b"\x04" + x + y)


async def _authenticate(request: Request, registration: bool = False) -> SignedRequest:
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/jose+json":
        raise ACMEError("malformed", "Expected application/jose+json", 415)
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_JWS_BYTES:
            raise ACMEError("malformed", "JWS request body is too large", 413)
        raw.extend(chunk)
    try:
        jws = _json_object(bytes(raw))
        if set(jws) != {"protected", "payload", "signature"} or not all(
            isinstance(value, str) for value in jws.values()
        ):
            raise ValueError("Expected flattened JWS")
        protected = _json_object(decode_b64url(jws["protected"]))
        if protected["alg"] != "ES256":
            raise ACMEError("badSignatureAlgorithm", "Use ES256")
        if "crit" in protected or "b64" in protected:
            raise ValueError("Unsupported JWS header")
        url = acme_url(request.url.path.removeprefix(ACME_PREFIX + "/"))
        if protected["url"] != url or request.url.query:
            raise ACMEError("malformed", "JWS URL does not match this resource")
        if registration:
            if "kid" in protected:
                raise ValueError("Unexpected kid")
            key = _key_from_jwk(protected["jwk"])
            account = b64url(key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.CompressedPoint))
        else:
            prefix = acme_url("account/")
            kid = protected["kid"]
            if "jwk" in protected or not isinstance(kid, str) or not kid.startswith(prefix):
                raise ACMEError("accountDoesNotExist", "Unknown ACME account")
            account = kid.removeprefix(prefix)
            point = decode_b64url(account)
            if len(point) != 33 or not account_exists(account):
                raise ACMEError("accountDoesNotExist", "Unknown ACME account")
            key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), point)
        signature = decode_b64url(jws["signature"])
        if len(signature) != 64:
            raise ValueError("Invalid ES256 signature length")
        r, s = int.from_bytes(signature[:32]), int.from_bytes(signature[32:])
        key.verify(
            utils.encode_dss_signature(r, s),
            f"{jws['protected']}.{jws['payload']}".encode("ascii"),
            ec.ECDSA(hashes.SHA256()),
        )
        nonce = protected.get("nonce")
        if not isinstance(nonce, str) or len(nonce) != 43:
            raise ACMEError("badNonce", "Missing or invalid replay nonce")
        consume_nonce(nonce)
        payload = _json_object(decode_b64url(jws["payload"])) if jws["payload"] else None
        return SignedRequest(account, payload)
    except InvalidSignature as exc:
        raise ACMEError("unauthorized", "Invalid JWS signature", 403) from exc
    except (KeyError, TypeError, ValueError, RecursionError) as exc:
        raise ACMEError("malformed", "Invalid ACME JWS request") from exc


async def new_account_request(request: Request) -> SignedRequest:
    """Verify possession of the account key supplied in the protected JWS header."""
    return await _authenticate(request, registration=True)


async def signed_request(request: Request) -> SignedRequest:
    """Verify signature and consume a nonce for a registered account."""
    return await _authenticate(request)
