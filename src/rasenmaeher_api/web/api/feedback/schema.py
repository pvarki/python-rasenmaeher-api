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
                    "version": "1.0.0",
                }
            ]
        },
    )

    role: str | None = Field(default=None, description="User type/role reported by the client")
    os: str | None = Field(default=None, description="Client OS")
    rating: str = Field(description="User's rating selection")
    comments: str = Field(description="Free-form feedback text")
    version: str | None = Field(default=None, description="Frontend app version")


class FeedbackOut(BaseModel):
    """Result of forwarding feedback to JOKE."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"ok": True}]},
    )

    ok: bool = Field(description="Whether the feedback was accepted and forwarded")
