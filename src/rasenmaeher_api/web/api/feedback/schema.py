"""Schema for feedback."""

from pydantic import BaseModel, ConfigDict, Field


class FeedbackIn(BaseModel):
    """Feedback submitted by a user from the app's feedback dialog."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "role": "admin",
                    "os": "macos",
                    "rating": "good",
                    "comments": "Works great, minor UI nit on mobile.",
                    "version": "2.6.0+260729",
                    "web_address": "https://example.pvarki.fi/app/settings",
                }
            ]
        },
    )

    rating: str = Field(max_length=64, description="User's rating selection")
    comments: str = Field(max_length=5000, description="Free-form feedback text")
    role: str | None = Field(default=None, max_length=64, description="User type/role reported by the client")
    os: str | None = Field(default=None, max_length=64, description="Client OS")
    version: str | None = Field(default=None, max_length=64, description="Frontend build version")
    web_address: str | None = Field(default=None, max_length=2048, description="Page the feedback was sent from")


class FeedbackOut(BaseModel):
    """Result of forwarding feedback to the configured ingest."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"ok": True}]},
    )

    ok: bool = Field(description="Whether the feedback was accepted and forwarded")
