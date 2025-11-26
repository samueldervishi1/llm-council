from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict


class ModelProvider(str, Enum):
    OPENROUTER = "openrouter"
    GOOGLE = "google"


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: ModelProvider


class QueryRequest(BaseModel):
    question: str


class ModelResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    model_name: str
    response: str
    error: Optional[str] = None


class PeerReview(BaseModel):
    reviewer_model: str
    rankings: List[Dict[str, Any]]


class CouncilSession(BaseModel):
    id: str
    question: str
    responses: List[ModelResponse] = []
    peer_reviews: List[PeerReview] = []
    final_synthesis: Optional[str] = None
    status: str = "pending"


class SynthesisRequest(BaseModel):
    session_id: str


class SessionResponse(BaseModel):
    session: CouncilSession
    message: str


class SessionSummary(BaseModel):
    id: str
    question: str
    status: str
    created_at: Optional[str] = None


class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]
    count: int
