"""Schema for product mTLS cert signing"""

from pydantic import BaseModel, Field, Extra


class CertificatesResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Respond with signed client cert and CA chain"""

    ca: str = Field(description="CA chain, cfssl encoded (newlines -> \\n)")
    certificate: str = Field(description="Signed cert, cfssl encoded (newlines -> \\n)")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "ca": """-----BEGIN CERTIFICATE-----\\nMIID9...\\n-----END CERTIFICATE-----\\n""",
                    "certificate": """-----BEGIN CERTIFICATE-----\\nMIID9...\\n-----END CERTIFICATE-----\\n""",
                },
            ]
        }


class CertificatesRequest(BaseModel):  # pylint: disable=too-few-public-methods
    """Request signed cert"""

    csr: str = Field(description="CSR PEM")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
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
        }


class RevokeRequest(BaseModel):  # pylint: disable=too-few-public-methods
    """Request a cert to be revoked"""

    cert: str = Field(description="Cert PEM")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
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
        }
