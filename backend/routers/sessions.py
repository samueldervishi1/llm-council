import uuid

from fastapi import APIRouter, HTTPException, Depends

from core.dependencies import get_session_repository, get_openrouter_client
from db import SessionRepository
from schemas import (
    QueryRequest,
    SessionResponse,
    CouncilSession,
    SessionListResponse,
    SessionSummary,
)
from services import CouncilService

router = APIRouter(prefix="/session", tags=["sessions"])


def get_council_service(client=Depends(get_openrouter_client)) -> CouncilService:
    return CouncilService(client)


@router.get("s", response_model=SessionListResponse)
async def list_sessions(
        limit: int = 50,
        repo: SessionRepository = Depends(get_session_repository)
):
    """List all sessions ordered by most recent."""
    sessions = await repo.list_all(limit=limit)
    summaries = []
    for s in sessions:
        created_at = s.get("created_at")
        summaries.append(SessionSummary(
            id=s["id"],
            question=s["question"],
            status=s["status"],
            created_at=created_at.isoformat() if created_at else None
        ))
    return SessionListResponse(sessions=summaries, count=len(summaries))


@router.post("", response_model=SessionResponse)
async def create_session(
        request: QueryRequest,
        repo: SessionRepository = Depends(get_session_repository)
):
    """Start a new council session with a question."""
    session_id = str(uuid.uuid4())

    session = CouncilSession(
        id=session_id,
        question=request.question,
        status="pending"
    )

    await repo.create(session)

    return SessionResponse(
        session=session,
        message="Session created. Call /session/{id}/responses to get council responses."
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
        session_id: str,
        repo: SessionRepository = Depends(get_session_repository)
):
    """Get the current state of a session."""
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session=session,
        message="Session retrieved"
    )


@router.delete("/{session_id}")
async def delete_session(
        session_id: str,
        repo: SessionRepository = Depends(get_session_repository)
):
    """Delete a session."""
    deleted = await repo.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}


@router.post("/{session_id}/responses", response_model=SessionResponse)
async def get_responses(
        session_id: str,
        repo: SessionRepository = Depends(get_session_repository),
        council_service: CouncilService = Depends(get_council_service)
):
    """Get responses from all council members."""
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "pending":
        return SessionResponse(
            session=session,
            message="Responses already collected"
        )

    responses = await council_service.get_council_responses(session)
    session.responses = responses
    session.status = "responses_complete"

    await repo.update(session)

    return SessionResponse(
        session=session,
        message="All council responses collected. Call /session/{id}/reviews for peer reviews."
    )


@router.post("/{session_id}/reviews", response_model=SessionResponse)
async def get_reviews(
        session_id: str,
        repo: SessionRepository = Depends(get_session_repository),
        council_service: CouncilService = Depends(get_council_service)
):
    """Have each council member review and rank the others' responses."""
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "pending":
        raise HTTPException(status_code=400, detail="Must collect responses first")

    if session.status in ["reviews_complete", "synthesized"]:
        return SessionResponse(
            session=session,
            message="Reviews already collected"
        )

    valid_responses = [r for r in session.responses if not r.error]

    if len(valid_responses) < 2:
        session.status = "reviews_complete"
        await repo.update(session)
        return SessionResponse(
            session=session,
            message="Not enough valid responses for peer review"
        )

    reviews = await council_service.get_peer_reviews(session)
    session.peer_reviews = reviews
    session.status = "reviews_complete"

    await repo.update(session)

    return SessionResponse(
        session=session,
        message="Peer reviews complete. Call /session/{id}/synthesize for final answer."
    )


@router.post("/{session_id}/synthesize", response_model=SessionResponse)
async def synthesize(
        session_id: str,
        repo: SessionRepository = Depends(get_session_repository),
        council_service: CouncilService = Depends(get_council_service)
):
    """Have the chairman synthesize a final response."""
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "synthesized":
        return SessionResponse(
            session=session,
            message="Already synthesized"
        )

    if session.status == "pending":
        raise HTTPException(status_code=400, detail="Must collect responses first")

    try:
        final_response = await council_service.synthesize_response(session)
        session.final_synthesis = final_response
        session.status = "synthesized"

        await repo.update(session)

        return SessionResponse(
            session=session,
            message="Synthesis complete!"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


@router.post("/{session_id}/run-all", response_model=SessionResponse)
async def run_full_council(
        session_id: str,
        repo: SessionRepository = Depends(get_session_repository),
        council_service: CouncilService = Depends(get_council_service)
):
    """Run the full council process: responses -> reviews -> synthesis."""
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Step 1: Get responses
    if session.status == "pending":
        responses = await council_service.get_council_responses(session)
        session.responses = responses
        session.status = "responses_complete"
        await repo.update(session)

    # Step 2: Get peer reviews
    if session.status == "responses_complete":
        reviews = await council_service.get_peer_reviews(session)
        session.peer_reviews = reviews
        session.status = "reviews_complete"
        await repo.update(session)

    # Step 3: Synthesize
    if session.status == "reviews_complete":
        final_response = await council_service.synthesize_response(session)
        session.final_synthesis = final_response
        session.status = "synthesized"
        await repo.update(session)

    return SessionResponse(
        session=session,
        message="Full council process complete!"
    )
