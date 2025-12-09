from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from .schemas import SessionSummary, SpeedStat, TypingSample


class _SessionData:
    """Internal structure to hold session aggregates."""

    __slots__ = ("session_id", "total_chars", "total_duration_ms", "samples_count", "last_updated")

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.total_chars: int = 0
        self.total_duration_ms: int = 0
        self.samples_count: int = 0
        self.last_updated: datetime = datetime.now(timezone.utc)

    def to_summary(self) -> SessionSummary:
        """Convert to SessionSummary Pydantic model."""
        avg_wpm = _compute_wpm(self.total_chars, self.total_duration_ms)
        return SessionSummary(
            session_id=self.session_id,
            total_chars=self.total_chars,
            total_duration_ms=self.total_duration_ms,
            avg_wpm=avg_wpm,
            samples_count=self.samples_count,
            last_updated=self.last_updated,
        )


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _compute_wpm(total_chars: int, total_duration_ms: int) -> float:
    """Compute words per minute given totals.

    WPM = (total_chars / 5) / (total_duration_ms / 60000)
    Guard against division by zero.
    """
    if total_duration_ms <= 0:
        return 0.0
    words = total_chars / 5.0
    minutes = total_duration_ms / 60000.0
    return words / minutes


class InMemoryTypingStore:
    """Thread-safe in-memory store for typing sessions and samples.

    The store aggregates stats per session and computes WPM.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: Dict[str, _SessionData] = {}

    # PUBLIC_INTERFACE
    def create_or_get_session(self, session_id: Optional[str] = None) -> str:
        """Create a new session or get existing one.

        Args:
            session_id: Optional explicit session id; if None, a new uuid4 is generated.

        Returns:
            The session id.
        """
        with self._lock:
            sid = session_id or str(uuid4())
            if sid not in self._sessions:
                self._sessions[sid] = _SessionData(sid)
            return sid

    # PUBLIC_INTERFACE
    def add_samples(self, session_id: str, samples: List[TypingSample]) -> SessionSummary:
        """Add samples to a session and update aggregates.

        Args:
            session_id: The target session id.
            samples: List of TypingSample to add.

        Returns:
            Updated SessionSummary.

        Raises:
            KeyError: If the session does not exist.
            ValueError: If samples contain invalid values (negative numbers or mismatched session ids).
        """
        if not samples:
            raise ValueError("samples must be non-empty")

        with self._lock:
            if session_id not in self._sessions:
                raise KeyError("session not found")

            sess = self._sessions[session_id]

            for s in samples:
                if s.session_id != session_id:
                    raise ValueError("sample.session_id does not match request session_id")
                if s.chars_typed < 0 or s.duration_ms < 0:
                    raise ValueError("chars_typed and duration_ms must be non-negative")

                sess.total_chars += s.chars_typed
                sess.total_duration_ms += s.duration_ms
                sess.samples_count += 1
                # last_updated should reflect the latest sample timestamp if available, else now
                sess.last_updated = max(sess.last_updated, s.timestamp.replace(tzinfo=timezone.utc) if s.timestamp.tzinfo else s.timestamp.replace(tzinfo=timezone.utc))

            # Ensure last_updated is at least now (in case of past timestamps)
            sess.last_updated = max(sess.last_updated, _now_utc())

            return sess.to_summary()

    # PUBLIC_INTERFACE
    def get_session_summary(self, session_id: str) -> SessionSummary:
        """Get the aggregate summary for a session.

        Raises:
            KeyError if session not found.
        """
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError("session not found")
            return self._sessions[session_id].to_summary()

    # PUBLIC_INTERFACE
    def get_session_stats(self, session_id: str) -> SpeedStat:
        """Get computed speed stats (WPM) for a session.

        Raises:
            KeyError if session not found.
        """
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError("session not found")
            sess = self._sessions[session_id]
            wpm = _compute_wpm(sess.total_chars, sess.total_duration_ms)
            return SpeedStat(
                session_id=session_id,
                wpm=wpm,
                accuracy=None,  # Reserved for future expansion
                last_updated=sess.last_updated,
            )

    # PUBLIC_INTERFACE
    def list_sessions(self) -> List[SessionSummary]:
        """List summaries for all sessions."""
        with self._lock:
            return [s.to_summary() for s in self._sessions.values()]

    # PUBLIC_INTERFACE
    def clear_session(self, session_id: str) -> None:
        """Delete a session and its aggregates.

        Raises:
            KeyError if session not found.
        """
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError("session not found")
            del self._sessions[session_id]


# Singleton store instance for app-wide usage
store = InMemoryTypingStore()
