"""Healthcheck response schemas"""
from typing import Dict

from pydantic import BaseModel, Field, Extra


class BasicHealthCheckResponse(BaseModel):
    """Basic healthcheck, basically are we running at all..."""

    healthcheck: str = Field(description="Should contain 'success'")
    dns: str = Field(description="Contains the FQDN of this instance")
    deployment: str = Field(description="Contains the deployment name of this instance (host part of the FQDN)")
    version: str = Field(description="Version number of the deployment (from ENV)")
    rm_version: str = Field(description="Version of the API package")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "healthcheck": "success",
                    "dns": "sleepy-sloth.pvarki.fi",
                    "deployment": "sleepy-sloth",
                    "version": "1.6.0",
                    "rm_version": "1.0.0",
                }
            ]
        }


class AllProductsHealthCheckResponse(BaseModel):
    """Check status of all products in manifest"""

    all_ok: bool = Field(description="Is everything ok ?")
    products: Dict[str, bool] = Field(description="Status for each product")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "all_ok": True,
                    "products": {
                        "tak": True,
                    },
                },
                {
                    "all_ok": False,
                    "products": {
                        "tak": True,
                        "other": False,
                    },
                },
            ]
        }
