from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# PUBLIC_INTERFACE
class SessionCreate(BaseModel):
    """Request model to create or get a typing session.

    Attributes:
        user_id: Optional identifier for the user (not used by backend store, provided for client correlation).
        session_id: Optional session id to reuse an existing session; one will be generated if not provided.
    """

    user_id: Optional[str] = Field(None, description="Optional user identifier.")
    session_id: Optional[str] = Field(
        None, description="Optional session id. If not provided, a new one will be generated."
    )


# PUBLIC_INTERFACE
class TypingSample(BaseModel):
    """A typing sample captured over a short time interval.

    Attributes:
        session_id: The session to which this sample belongs.
        timestamp: The timestamp at which the sample was recorded.
        chars_typed: Number of characters typed in the interval (must be >= 0).
        duration_ms: Duration of the interval in milliseconds (must be >= 0).
    """

    session_id: str = Field(..., description="Session identifier to associate the sample with.")
    timestamp: datetime = Field(..., description="Timestamp when the sample was recorded.")
    chars_typed: int = Field(..., ge=0, description="Number of characters typed (>= 0).")
    duration_ms: int = Field(..., ge=0, description="Duration in milliseconds (>= 0).")

    @field_validator("session_id")
    @classmethod
    def session_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("session_id must be a non-empty string")
        return v


# PUBLIC_INTERFACE
class SubmissionRequest(BaseModel):
    """Request model for submitting multiple typing samples for a session.

    Attributes:
        session_id: Target session id.
        samples: List of TypingSample for the given session (cannot be empty).
    """

    session_id: str = Field(..., description="Target session id for the submission.")
    samples: List[TypingSample] = Field(..., description="List of typing samples (must be non-empty).")

    @field_validator("samples")
    @classmethod
    def samples_not_empty(cls, v: List[TypingSample]) -> List[TypingSample]:
        if not v:
            raise ValueError("samples must be a non-empty list")
        return v


# PUBLIC_INTERFACE
class SpeedStat(BaseModel):
    """Computed speed statistics for a session.

    Attributes:
        session_id: Session identifier.
        wpm: Words per minute computed as (total_chars / 5) / (total_duration_ms / 60000).
        accuracy: Optional accuracy percentage (reserved for future use).
        last_updated: Timestamp when stats were last updated.
    """

    session_id: str = Field(..., description="Session identifier.")
    wpm: float = Field(..., description="Computed words per minute.")
    accuracy: Optional[float] = Field(
        None, description="Optional accuracy value in range [0, 100]."
    )
    last_updated: datetime = Field(..., description="Last update timestamp.")


# PUBLIC_INTERFACE
class SessionSummary(BaseModel):
    """Aggregated summary of samples for a session.

    Attributes:
        session_id: Session identifier.
        total_chars: Total characters typed across all samples.
        total_duration_ms: Total duration across all samples in milliseconds.
        avg_wpm: Average words per minute across the session.
        samples_count: Number of samples added to the session.
        last_updated: Timestamp when the session was last updated.
    """

    session_id: str = Field(..., description="Session identifier.")
    total_chars: int = Field(..., ge=0, description="Total characters typed (>= 0).")
    total_duration_ms: int = Field(..., ge=0, description="Total duration in ms (>= 0).")
    avg_wpm: float = Field(..., ge=0, description="Average words per minute (>= 0).")
    samples_count: int = Field(..., ge=0, description="Number of samples aggregated (>= 0).")
    last_updated: datetime = Field(..., description="Last update timestamp.")
