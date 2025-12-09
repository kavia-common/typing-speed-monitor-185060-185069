from __future__ import annotations

from fastapi import APIRouter, HTTPException
from starlette import status

from ..schemas import (
    SessionCreate,
    SessionSummary,
    SpeedStat,
    SubmissionRequest,
)
from ..storage import store

typing_router = APIRouter(prefix="/typing", tags=["typing"])


@typing_router.post(
    "/session",
    summary="Create or get a typing session",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
# PUBLIC_INTERFACE
def create_session(payload: SessionCreate) -> dict:
    """Create a new session or return an existing one.

    Parameters:
        payload: SessionCreate with optional session_id.

    Returns:
        JSON object with generated or existing session_id.
    """
    session_id = store.create_or_get_session(payload.session_id)
    return {"session_id": session_id}


@typing_router.post(
    "/submit",
    summary="Submit typing samples for a session",
    response_model=SessionSummary,
    status_code=status.HTTP_200_OK,
)
# PUBLIC_INTERFACE
def submit_samples(request: SubmissionRequest) -> SessionSummary:
    """Submit one or more typing samples and update aggregates.

    Validates:
      - samples is non-empty
      - sample.session_id matches request.session_id
      - chars_typed and duration_ms are non-negative

    Parameters:
        request: SubmissionRequest containing session_id and samples.

    Returns:
        Updated SessionSummary.

    Raises:
        HTTPException 400 for invalid input.
        HTTPException 404 if session does not exist.
    """
    if not request.samples:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="samples must be non-empty")

    # Basic validation of non-negative fields and matching session ids
    for s in request.samples:
        if s.session_id != request.session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="sample.session_id does not match request.session_id",
            )
        if s.chars_typed < 0 or s.duration_ms < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="chars_typed and duration_ms must be non-negative",
            )

    try:
        summary = store.add_samples(request.session_id, request.samples)
        return summary
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@typing_router.get(
    "/summary/{session_id}",
    summary="Get session summary",
    response_model=SessionSummary,
    status_code=status.HTTP_200_OK,
)
# PUBLIC_INTERFACE
def get_summary(session_id: str) -> SessionSummary:
    """Retrieve the aggregated session summary.

    Parameters:
        session_id: The session identifier.

    Returns:
        SessionSummary for the session.

    Raises:
        HTTPException 404 if session not found.
    """
    try:
        return store.get_session_summary(session_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")


@typing_router.get(
    "/stats/{session_id}",
    summary="Get session typing speed statistics",
    response_model=SpeedStat,
    status_code=status.HTTP_200_OK,
)
# PUBLIC_INTERFACE
def get_stats(session_id: str) -> SpeedStat:
    """Retrieve computed typing speed statistics for a session.

    Parameters:
        session_id: The session identifier.

    Returns:
        SpeedStat (including WPM).

    Raises:
        HTTPException 404 if session not found.
    """
    try:
        return store.get_session_stats(session_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")


@typing_router.get(
    "/sessions",
    summary="List all sessions",
    response_model=list[SessionSummary],
    status_code=status.HTTP_200_OK,
)
# PUBLIC_INTERFACE
def list_sessions() -> list[SessionSummary]:
    """List summaries of all existing sessions."""
    return store.list_sessions()


@typing_router.delete(
    "/session/{session_id}",
    summary="Delete a session and its data",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
# PUBLIC_INTERFACE
def delete_session(session_id: str) -> dict:
    """Delete a session.

    Parameters:
        session_id: The session identifier.

    Returns:
        {"status":"deleted"} on success.

    Raises:
        HTTPException 404 if session not found.
    """
    try:
        store.clear_session(session_id)
        return {"status": "deleted"}
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
