"""Healthcheck response schemas"""
from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """Healthcheck response schema"""

    healthcheck: str
    dns: str
