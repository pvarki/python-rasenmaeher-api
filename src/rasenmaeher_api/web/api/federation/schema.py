"""Public federation contract, mirrored by takintegration without a shared package."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_peer(value: str) -> str:
    """Accept only a deployment DNS authority and an optional HTTPS port."""
    match = re.fullmatch(r"([A-Za-z0-9.-]+)(?::([0-9]{1,5}))?", value)
    if not match:
        raise ValueError("Expected a deployment DNS hostname with an optional HTTPS port")
    host, port_text = match.groups()
    host = host.lower()
    labels = host.split(".")
    if (
        len(host) > 249  # Leave room for the derived 'tak.' hostname.
        or len(labels) < 2
        or host.startswith("tak.")
        or all(label.isdigit() for label in labels)
        or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)
    ):
        raise ValueError("Invalid deployment DNS hostname")
    port = int(port_text) if port_text else 443
    if not 1 <= port <= 65535:
        raise ValueError("Invalid HTTPS port")
    if len(labels[0]) > 30:
        raise ValueError("Derived TAK display name exceeds 30 characters")
    return host if port == 443 else f"{host}:{port}"


class FederationRequest(BaseModel):
    """No caller-selected URL, group or federation settings."""

    model_config = ConfigDict(extra="forbid")
    remote_base: str

    _normalize_peer = field_validator("remote_base")(normalize_peer)

    @property
    def hostname(self) -> str:
        """HTTPS port is not part of federation identity."""
        return self.remote_base.split(":")[0]

    @property
    def display_name(self) -> str:
        """TAK rejects hyphens in display names."""
        return self.hostname.split(".")[0].replace("-", "_")


class FederationTrustResponse(BaseModel):
    """Verified local CA and group configuration."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: Literal[True]
    operation: Literal["trust"]
    remote_base: str
    changed: bool
    ca_fingerprint: str = Field(pattern=r"^(?:[0-9A-F]{2}:){31}[0-9A-F]{2}$")
    group: Literal["default"]
    directions: list[Literal["INBOUND", "OUTBOUND"]]

    @field_validator("directions")
    @classmethod
    def both_directions(cls, value: list[Literal["INBOUND", "OUTBOUND"]]) -> list[Literal["INBOUND", "OUTBOUND"]]:
        """A successful trust response must confirm both directions."""
        if value != ["INBOUND", "OUTBOUND"]:
            raise ValueError("Both default group directions are required")
        return value


class FederationOutgoingResponse(BaseModel):
    """Configuration success does not imply delivered traffic."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: Literal[True]
    operation: Literal["outgoing"]
    remote_base: str
    changed: bool
    display_name: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9_\s]+$")
    address: str
    port: Literal[9001]
    protocol_version: Literal[2]
    enabled: Literal[True]
    connection_status: str | None
