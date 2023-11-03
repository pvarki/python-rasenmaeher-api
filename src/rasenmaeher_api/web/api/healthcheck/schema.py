"""Healthcheck response schemas"""
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Healthcheck response schema"""

    healthcheck: str = Field(description="Should contain 'success'")
    dns: str = Field(description="Contains the FQDN of this instance")
    deployment: str = Field(description="Contains the deployment name of this instance (host part of the FQDN)")
