from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, Field


class ModelProvider(str, Enum):
    """Supported LLM providers."""
    OPENROUTER = "openrouter"
    GOOGLE = "google"


class ModelInfo(BaseModel):
    """Information about a configured LLM model."""
    id: str = Field(..., description="Unique model identifier (e.g., 'openai/gpt-4')")
    name: str = Field(..., description="Human-readable model name")
    provider: ModelProvider = Field(..., description="The provider hosting this model")


class QueryRequest(BaseModel):
    """Request to start a new council session."""
    question: str = Field(
        ...,
        description="The question or prompt to send to all council members",
        min_length=1,
        json_schema_extra={"example": "What are the best practices for building scalable APIs?"}
    )


class ContinueRequest(BaseModel):
    """Request to continue an existing session with a follow-up question."""
    question: str = Field(
        ...,
        description="The follow-up question for the next round of deliberation",
        min_length=1,
        json_schema_extra={"example": "Can you elaborate on the caching strategies mentioned?"}
    )


class ModelResponse(BaseModel):
    """Response from a single council member (LLM)."""
    model_config = ConfigDict(protected_namespaces=())

    model_id: str = Field(..., description="The model's unique identifier")
    model_name: str = Field(..., description="Human-readable name of the model")
    response: str = Field(..., description="The model's response to the question")
    error: Optional[str] = Field(None, description="Error message if the model failed to respond")


class PeerReview(BaseModel):
    """A peer review where one model evaluates other models' responses."""
    reviewer_model: str = Field(..., description="The model that performed this review")
    rankings: List[Dict[str, Any]] = Field(
        ...,
        description="Ranked list of other models' responses with scores and reasoning"
    )


class ConversationRound(BaseModel):
    """
    A single round of council deliberation.

    Each round consists of:
    1. A question posed to the council
    2. Responses from each council member
    3. Peer reviews where models evaluate each other
    4. A final synthesis by the chairman
    """
    question: str = Field(..., description="The question for this round")
    responses: List[ModelResponse] = Field(
        default=[],
        description="Responses from all council members"
    )
    peer_reviews: List[PeerReview] = Field(
        default=[],
        description="Peer reviews from each council member"
    )
    final_synthesis: Optional[str] = Field(
        None,
        description="The chairman's synthesized final answer"
    )
    status: str = Field(
        default="pending",
        description="Current status: pending, responses_complete, reviews_complete, or synthesized"
    )
    disagreement_analysis: Optional[List[dict]] = Field(
        default=None,
        description="Analysis of disagreement among council members"
    )


class CouncilSession(BaseModel):
    """
    A council session containing one or more rounds of deliberation.

    Sessions persist across multiple rounds, allowing for follow-up questions
    and continued conversation with context from previous rounds.
    """
    id: str = Field(..., description="Unique session identifier (UUID)")
    title: Optional[str] = Field(None, description="Session title (derived from first question)")
    rounds: List[ConversationRound] = Field(
        default=[],
        description="All conversation rounds in this session"
    )
    is_deleted: bool = Field(default=False, description="Whether the session has been soft-deleted")
    deleted_at: Optional[str] = Field(None, description="ISO timestamp when session was deleted")
    # Sharing fields
    is_shared: bool = Field(default=False, description="Whether the session is publicly shared")
    share_token: Optional[str] = Field(None, description="Unique token for public sharing")
    shared_at: Optional[str] = Field(None, description="ISO timestamp when session was shared")


class SynthesisRequest(BaseModel):
    """Request to synthesize responses for a session."""
    session_id: str = Field(..., description="The session ID to synthesize")


class SessionResponse(BaseModel):
    """Standard response containing session data and a status message."""
    session: CouncilSession = Field(..., description="The full session object")
    message: str = Field(..., description="Status message about the operation")


class SessionSummary(BaseModel):
    """Brief summary of a session for listing purposes."""
    id: str = Field(..., description="Session ID")
    title: Optional[str] = Field(None, description="Session title")
    question: str = Field(..., description="The initial question")
    status: str = Field(..., description="Current session status")
    round_count: int = Field(default=1, description="Number of conversation rounds")
    created_at: Optional[str] = Field(None, description="ISO timestamp of creation")


class SessionListResponse(BaseModel):
    """Response containing a list of session summaries."""
    sessions: List[SessionSummary] = Field(..., description="List of session summaries")
    count: int = Field(..., description="Total number of sessions returned")


class ShareResponse(BaseModel):
    """Response when sharing a session."""
    share_token: str = Field(..., description="Unique token for accessing the shared session")
    share_url: str = Field(..., description="Full URL to access the shared session")
    message: str = Field(..., description="Status message")


class DisagreementAnalysis(BaseModel):
    """Analysis of disagreement among council members for a response."""
    model_id: str = Field(..., description="The model whose response was analyzed")
    model_name: str = Field(..., description="Human-readable model name")
    ranks_received: List[int] = Field(default=[], description="All ranks given by reviewers")
    mean_rank: float = Field(default=0.0, description="Average rank")
    disagreement_score: float = Field(
        default=0.0,
        description="Disagreement score from 0 (consensus) to 1 (high disagreement)"
    )
    has_disagreement: bool = Field(default=False, description="Whether significant disagreement exists")
