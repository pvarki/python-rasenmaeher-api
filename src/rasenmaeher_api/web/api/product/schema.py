"""Schema for product mTLS cert signing"""

from pydantic import BaseModel, Field, ConfigDict


class CertificatesResponse(BaseModel):
    """Respond with signed client cert and CA chain"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "ca": """-----BEGIN CERTIFICATE-----\\nMIID9...\\n-----END CERTIFICATE-----\\n""",
                    "certificate": """-----BEGIN CERTIFICATE-----\\nMIID9...\\n-----END CERTIFICATE-----\\n""",
                },
            ]
        },
    )

    ca: str = Field(description="CA chain, cfssl encoded (newlines -> \\n)")
    certificate: str = Field(description="Signed cert, cfssl encoded (newlines -> \\n)")


class CertificatesRequest(BaseModel):
    """Request signed cert"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "csr": """-----BEGIN CERTIFICATE REQUEST-----
MIIENzCCAx+gAwIBAgIUYI++L/D00OIhBba4cixT5aJrw+wwDQYJKoZIhvcNAQEL
...
0TdCAC4q4VuW+1FYcLrBkZhJZDnPRn214POSwN5lRmkYfUK40VGBRJMhgaI6Iud/
yiIpfvrcT9M4hJwtVFZy
-----END CERTIFICATE REQUEST-----"""
                },
            ]
        },
    )

    csr: str = Field(description="CSR PEM")


class RevokeRequest(BaseModel):
    """Request a cert to be revoked"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "cert": """-----BEGIN CERTIFICATE-----
MIID9DCCAtygAwIBAgIUSF7KldQcZ9tc8IHB9zBQnf/1V58wDQYJKoZIhvcNAQEL
...
RTM/xsm9FVNDBFy/w5Xu6Xewa5UrHkRtrEsbmhbbc6VLytoQrhgqV6kbFJP8vgFn
zPs4ufNJed0=
-----END CERTIFICATE-----"""
                },
            ]
        },
    )

    cert: str = Field(description="Cert PEM")


class KCClientToken(BaseModel):
    """Token for registering a KC client (for OIDC)"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "id": """ca27c7ee-bc2b-4a48-bd76-9f12d31758bb""",
                    "certificate": """eyJhb...._N8GEsPw""",
                    "timestamp": 1743207161,
                    "expiration": 1,
                    "count": 1,
                    "remainingCount": 1,
                },
            ]
        },
    )

    id: str = Field(description="Internal KC uuid for the token")
    token: str = Field(description="JWT that allows to register a client to KC")
    timestamp: int = Field(description="Unix timestamp")
    expiration: int = Field(description="Expires in days")
    count: int = Field(description="Number of uses total")
    remainingCount: int = Field(description="Number of uses remaining")


# FIXME: Move to libpvarki
class ProductAddRequest(BaseModel):
    """Request to add product interoperability."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "certcn": "product.deployment.tld",
                    "x509cert": "-----BEGIN CERTIFICATE-----\\nMIIEwjCC...\\n-----END CERTIFICATE-----\\n",
                },
            ],
        },
    )

    certcn: str = Field(description="CN of the certificate")
    x509cert: str = Field(description="Certificate encoded with CFSSL conventions (newlines escaped)")


class ProductAuthzRequest(BaseModel):  # pylint: disable=too-few-public-methods
    """Request authz for a specific source product."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "certcn": "product.deployment.tld",
                },
            ],
        },
    )

    certcn: str = Field(description="CN of the source product certificate")


class ProductAuthzResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Authz info for a product integration."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "type": "mtls",
                },
                {
                    "type": "bearer-token",
                    "token": "<JWT>",
                },
                {
                    "type": "basic",
                    "username": "product.deployment.tld",
                    "password": "<PASSWORD>",
                    "ro_password": "<PASSWORD>",
                },
            ],
        },
    )

    type: str = Field(description="type of authz: bearer-token, basic, mtls")
    token: str | None = Field(description="Bearer token", default=None)
    username: str | None = Field(description="Username for basic auth", default=None)
    password: str | None = Field(description="Password for basic auth", default=None)
    ro_password: str | None = Field(description="Password for read-only streaming", default=None)
