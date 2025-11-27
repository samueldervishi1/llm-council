import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Request

from core.dependencies import get_session_repository, get_openrouter_client
from db import SessionRepository
from schemas import (
    QueryRequest,
    ContinueRequest,
    SessionResponse,
    CouncilSession,
    ConversationRound,
    SessionListResponse,
    SessionSummary,
    ShareResponse,
)
from services import CouncilService
from services.council import analyze_disagreement

router = APIRouter(prefix="/session", tags=["sessions"])


def get_council_service(client=Depends(get_openrouter_client)) -> CouncilService:
    return CouncilService(client)


@router.get("s", response_model=SessionListResponse)
async def list_sessions(
        limit: int = 50,
        repo: SessionRepository = Depends(get_session_repository)
):
    """
    List All Sessions

    Retrieves a list of all council sessions, ordered by most recent first.
    Returns summary information for each session including title, status, and round count.

    - **limit**: Maximum number of sessions to return (default: 50)
    """
    sessions = await repo.list_all(limit=limit)
    summaries = []
    for s in sessions:
        created_at = s.get("created_at")
        summaries.append(SessionSummary(
            id=s["id"],
            title=s.get("title"),
            question=s["question"],
            status=s["status"],
            round_count=s.get("round_count", 1),
            created_at=created_at.isoformat() if created_at else None
        ))
    return SessionListResponse(sessions=summaries, count=len(summaries))


@router.post("", response_model=SessionResponse)
async def create_session(
        request: QueryRequest,
        repo: SessionRepository = Depends(get_session_repository)
):
    """
    Create New Session

    Starts a new council session with your question. This creates a session
    with a pending first round, ready for council deliberation.

    **Next step**: Call `POST /session/{id}/run-all` to run the full council
    process, or use individual endpoints for step-by-step control.
    """
    session_id = str(uuid.uuid4())

    # Create first round
    first_round = ConversationRound(
        question=request.question,
        status="pending"
    )

    session = CouncilSession(
        id=session_id,
        title=request.question[:100],  # Use first 100 chars as title
        rounds=[first_round]
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
    """
    Get Session Details

    Retrieves the complete state of a session including all rounds,
    responses, peer reviews, and synthesis results.
    """
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
    """
    Delete Session

    Soft-deletes a session. The session data is preserved but marked as deleted
    and will no longer appear in session lists.
    """
    deleted = await repo.soft_delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}


@router.post("/{session_id}/continue", response_model=SessionResponse)
async def continue_session(
        session_id: str,
        request: ContinueRequest,
        repo: SessionRepository = Depends(get_session_repository)
):
    """
    Continue Session

    Adds a follow-up question to an existing session, creating a new round.
    The previous round must be fully completed (synthesized) before continuing.

    This allows for multi-turn conversations where the council can build on
    previous context and answers.
    """
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if last round is complete
    if session.rounds:
        last_round = session.rounds[-1]
        if last_round.status != "synthesized":
            raise HTTPException(
                status_code=400,
                detail="Previous round must be completed before continuing"
            )

    # Add new round
    new_round = ConversationRound(
        question=request.question,
        status="pending"
    )
    session.rounds.append(new_round)

    await repo.update(session)

    return SessionResponse(
        session=session,
        message="New round added. Call /session/{id}/responses to get council responses."
    )


@router.post("/{session_id}/responses", response_model=SessionResponse)
async def get_responses(
        session_id: str,
        repo: SessionRepository = Depends(get_session_repository),
        council_service: CouncilService = Depends(get_council_service)
):
    """
    Collect Council Responses

    Queries all council member LLMs in parallel and collects their responses
    to the current round's question. Each model provides its independent answer.

    **Step 1 of 3** in the council deliberation process.

    **Next step**: Call `POST /session/{id}/reviews` for peer reviews.
    """
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.rounds:
        raise HTTPException(status_code=400, detail="No rounds in session")

    current_round = session.rounds[-1]
    previous_rounds = session.rounds[:-1] if len(session.rounds) > 1 else None

    if current_round.status != "pending":
        return SessionResponse(
            session=session,
            message="Responses already collected for this round"
        )

    responses = await council_service.get_council_responses(current_round, previous_rounds)
    current_round.responses = responses
    current_round.status = "responses_complete"

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
    """
    Collect Peer Reviews

    Each council member reviews and ranks the other models' responses.
    This provides multiple perspectives on the quality and accuracy of each answer.

    **Step 2 of 3** in the council deliberation process.
    Requires responses to be collected first.

    **Next step**: Call `POST /session/{id}/synthesize` for the final synthesis.
    """
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.rounds:
        raise HTTPException(status_code=400, detail="No rounds in session")

    current_round = session.rounds[-1]
    previous_rounds = session.rounds[:-1] if len(session.rounds) > 1 else None

    if current_round.status == "pending":
        raise HTTPException(status_code=400, detail="Must collect responses first")

    if current_round.status in ["reviews_complete", "synthesized"]:
        return SessionResponse(
            session=session,
            message="Reviews already collected for this round"
        )

    valid_responses = [r for r in current_round.responses if not r.error]

    if len(valid_responses) < 2:
        current_round.status = "reviews_complete"
        await repo.update(session)
        return SessionResponse(
            session=session,
            message="Not enough valid responses for peer review"
        )

    reviews = await council_service.get_peer_reviews(current_round, previous_rounds)
    current_round.peer_reviews = reviews
    current_round.status = "reviews_complete"

    # Analyze disagreement
    current_round.disagreement_analysis = analyze_disagreement(
        current_round.responses, current_round.peer_reviews
    )

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
    """
    Synthesize Final Answer

    The chairman model analyzes all council responses and peer reviews to
    produce a comprehensive, well-reasoned final answer that incorporates
    the best insights from each council member.

    **Step 3 of 3** in the council deliberation process.
    Completes the current round.

    **Next step**: Optionally call `POST /session/{id}/continue` to ask a follow-up question.
    """
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.rounds:
        raise HTTPException(status_code=400, detail="No rounds in session")

    current_round = session.rounds[-1]
    previous_rounds = session.rounds[:-1] if len(session.rounds) > 1 else None

    if current_round.status == "synthesized":
        return SessionResponse(
            session=session,
            message="Already synthesized for this round"
        )

    if current_round.status == "pending":
        raise HTTPException(status_code=400, detail="Must collect responses first")

    try:
        final_response = await council_service.synthesize_response(current_round, previous_rounds)
        current_round.final_synthesis = final_response
        current_round.status = "synthesized"

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
    """
    Run Full Council Process

    Executes the complete council deliberation in one call:

    1. **Collect Responses** - Query all council members
    2. **Peer Reviews** - Each model evaluates the others
    3. **Synthesis** - Chairman produces the final answer

    This is the recommended endpoint for most use cases. Use the individual
    step endpoints (`/responses`, `/reviews`, `/synthesize`) only when you need
    fine-grained control over the process.
    """
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.rounds:
        raise HTTPException(status_code=400, detail="No rounds in session")

    current_round = session.rounds[-1]
    previous_rounds = session.rounds[:-1] if len(session.rounds) > 1 else None

    # Step 1: Get responses
    if current_round.status == "pending":
        responses = await council_service.get_council_responses(current_round, previous_rounds)
        current_round.responses = responses
        current_round.status = "responses_complete"
        await repo.update(session)

    # Step 2: Get peer reviews
    if current_round.status == "responses_complete":
        reviews = await council_service.get_peer_reviews(current_round, previous_rounds)
        current_round.peer_reviews = reviews
        current_round.status = "reviews_complete"
        # Analyze disagreement
        current_round.disagreement_analysis = analyze_disagreement(
            current_round.responses, current_round.peer_reviews
        )
        await repo.update(session)

    # Step 3: Synthesize
    if current_round.status == "reviews_complete":
        final_response = await council_service.synthesize_response(current_round, previous_rounds)
        current_round.final_synthesis = final_response
        current_round.status = "synthesized"
        await repo.update(session)

    return SessionResponse(
        session=session,
        message="Full council process complete!"
    )


@router.post("/{session_id}/share", response_model=ShareResponse)
async def share_session(
        session_id: str,
        request: Request,
        repo: SessionRepository = Depends(get_session_repository)
):
    """
    Share Session

    Generates a public share link for a session. Anyone with the link can view
    the session in read-only mode without authentication.

    Returns the share token and full URL for sharing.
    """
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Generate new share token if not already shared
    if not session.is_shared or not session.share_token:
        session.share_token = secrets.token_urlsafe(16)
        session.is_shared = True
        session.shared_at = datetime.now(timezone.utc).isoformat()
        await repo.update(session)

    # Build share URL from request
    base_url = str(request.base_url).rstrip('/')
    share_url = f"{base_url}/shared/{session.share_token}"

    return ShareResponse(
        share_token=session.share_token,
        share_url=share_url,
        message="Session shared successfully"
    )


@router.delete("/{session_id}/share")
async def unshare_session(
        session_id: str,
        repo: SessionRepository = Depends(get_session_repository)
):
    """
    Revoke Session Sharing

    Removes public access to a shared session. The share link will no longer work.
    """
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.is_shared:
        return {"message": "Session was not shared"}

    session.is_shared = False
    session.share_token = None
    session.shared_at = None
    await repo.update(session)

    return {"message": "Session sharing revoked"}


@router.get("/{session_id}/share-info")
async def get_share_info(
        session_id: str,
        request: Request,
        repo: SessionRepository = Depends(get_session_repository)
):
    """
    Get Share Info

    Returns the current sharing status and share URL if the session is shared.
    """
    session = await repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.is_shared or not session.share_token:
        return {
            "is_shared": False,
            "share_token": None,
            "share_url": None
        }

    base_url = str(request.base_url).rstrip('/')
    return {
        "is_shared": True,
        "share_token": session.share_token,
        "share_url": f"{base_url}/shared/{session.share_token}",
        "shared_at": session.shared_at
    }
