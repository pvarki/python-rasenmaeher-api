"""Schema for product mTLS cert signing"""
from pydantic import BaseModel, Field


class CertificatesResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Respond with signed client cert and CA chain"""

    ca: str = Field(description="CA chain, cfssl encoded (newlines -> \\n)")
    certificate: str = Field(description="Signed cert, cfssl encoded (newlines -> \\n)")

class CertificatesRequest(BaseModel):  # pylint: disable=too-few-public-methods
    """Request signed cert"""

    csr: str = Field(description="CSR, cfssl encoded (newlines -> \\n)")
