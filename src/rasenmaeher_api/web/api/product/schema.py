"""Schema for product mTLS cert signing"""
from pydantic import BaseModel, Field, Extra


class CertificatesResponse(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Respond with signed client cert and CA chain"""

    ca: str = Field(description="CA chain, cfssl encoded (newlines -> \\n)")
    certificate: str = Field(description="Signed cert, cfssl encoded (newlines -> \\n)")


class CertificatesRequest(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Request signed cert"""

    csr: str = Field(description="CSR, cfssl encoded (newlines -> \\n)")


class ReadyRequest(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Indicate product API readiness"""

    product: str = Field(description="Product name")
    apiurl: str = Field(description="Product API URL")
    url: str = Field(description="Product UI URL")


# FIXME: Move to libpvarki as generic response


class GenericResponse(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Generic ok/not-ok response"""

    ok: bool = Field(description="Is everything ok")
    message: str = Field(description="Any message", default="")
