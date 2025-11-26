import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import COUNCIL_MODELS, CHAIRMAN_MODEL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm-council")

from models import (
    QueryRequest,
    ModelResponse,
    PeerReview,
    CouncilSession,
    SessionResponse
)
from clients import OpenRouterClient

# In-memory session storage
sessions: Dict[str, CouncilSession] = {}

# Initialize client
openrouter_client = OpenRouterClient()


@asynccontextmanager
async def lifespan():
    # Startup
    print("LLM Council API starting...")
    print(f"Council members: {[m['name'] for m in COUNCIL_MODELS]}")
    print(f"Chairman: {CHAIRMAN_MODEL['name']}")
    yield
    # Shutdown
    print("LLM Council API shutting down...")


app = FastAPI(
    title="LLM Council API",
    description="Query multiple LLMs and synthesize their responses",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "LLM Council API", "status": "running"}


@app.get("/models")
async def get_models():
    """Get the configured council models and chairman."""
    return {
        "council_models": COUNCIL_MODELS,
        "chairman_model": CHAIRMAN_MODEL
    }


@app.post("/query", response_model=SessionResponse)
async def create_query(request: QueryRequest):
    """Start a new council session with a question."""
    session_id = str(uuid.uuid4())

    session = CouncilSession(
        id=session_id,
        question=request.question,
        status="pending"
    )

    sessions[session_id] = session

    return SessionResponse(
        session=session,
        message="Session created. Call /session/{id}/responses to get council responses."
    )


@app.post("/session/{session_id}/responses", response_model=SessionResponse)
async def get_council_responses(session_id: str):
    """Get responses from all council members."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if session.status != "pending":
        return SessionResponse(
            session=session,
            message="Responses already collected"
        )

    # Query all council models in parallel
    async def query_model(model: dict) -> ModelResponse:
        try:
            response = await openrouter_client.chat(
                model_id=model["id"],
                prompt=session.question,
                system_prompt="You are a helpful assistant participating in a council of AI models. Provide a direct, thoughtful, and concise answer to the user's question. Do NOT ask follow-up questions. Do NOT ask for clarification. Just give your best answer based on the question asked."
            )

            return ModelResponse(
                model_id=model["id"],
                model_name=model["name"],
                response=response
            )
        except Exception as e:
            return ModelResponse(
                model_id=model["id"],
                model_name=model["name"],
                response="",
                error=str(e)
            )

    # Execute all queries in parallel
    tasks = [query_model(model) for model in COUNCIL_MODELS]
    responses = await asyncio.gather(*tasks)

    session.responses = list(responses)
    session.status = "responses_complete"

    return SessionResponse(
        session=session,
        message="All council responses collected. Call /session/{id}/reviews for peer reviews."
    )


@app.post("/session/{session_id}/reviews", response_model=SessionResponse)
async def get_peer_reviews(session_id: str):
    """Have each council member review and rank the others' responses."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if session.status == "pending":
        raise HTTPException(status_code=400, detail="Must collect responses first")

    if session.status in ["reviews_complete", "synthesized"]:
        return SessionResponse(
            session=session,
            message="Reviews already collected"
        )

    # Filter out failed responses
    valid_responses = [r for r in session.responses if not r.error]

    if len(valid_responses) < 2:
        session.status = "reviews_complete"
        return SessionResponse(
            session=session,
            message="Not enough valid responses for peer review"
        )

    # Build the review prompt
    def build_review_prompt(reviewer_id: str) -> str:
        responses_text = ""
        for i, resp in enumerate(valid_responses):
            if resp.model_id != reviewer_id:
                responses_text += f"\n\n--- Response {i + 1} ---\n{resp.response}"

        return f"""You are reviewing responses from other AI models to the following question:

Question: {session.question}

Here are the anonymous responses:
{responses_text}

Please rank these responses from best to worst based on:
1. Accuracy and correctness
2. Clarity and helpfulness
3. Completeness

Provide your ranking as a JSON array with this format:
[
  {{"response_num": 1, "rank": 1, "reasoning": "Brief explanation"}},
  {{"response_num": 2, "rank": 2, "reasoning": "Brief explanation"}}
]

Only output the JSON array, nothing else."""

    async def get_review(model: dict) -> PeerReview:
        try:
            prompt = build_review_prompt(model["id"])

            response = await openrouter_client.chat(
                model_id=model["id"],
                prompt=prompt,
                temperature=0.3
            )

            # Try to parse JSON from response
            try:
                # Find JSON in response
                start = response.find('[')
                end = response.rfind(']') + 1
                if start != -1 and end > start:
                    rankings = json.loads(response[start:end])
                else:
                    rankings = []
            except json.JSONDecodeError:
                rankings = [{"raw_response": response}]

            return PeerReview(
                reviewer_model=model["name"],
                rankings=rankings
            )
        except Exception as e:
            return PeerReview(
                reviewer_model=model["name"],
                rankings=[{"error": str(e)}]
            )

    # Execute reviews in parallel
    tasks = [get_review(model) for model in COUNCIL_MODELS]
    reviews = await asyncio.gather(*tasks)

    session.peer_reviews = list(reviews)
    session.status = "reviews_complete"

    return SessionResponse(
        session=session,
        message="Peer reviews complete. Call /session/{id}/synthesize for final answer."
    )


@app.post("/session/{session_id}/synthesize", response_model=SessionResponse)
async def synthesize_response(session_id: str):
    """Have the chairman synthesize a final response."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if session.status == "synthesized":
        return SessionResponse(
            session=session,
            message="Already synthesized"
        )

    if session.status == "pending":
        raise HTTPException(status_code=400, detail="Must collect responses first")

    # Build synthesis prompt
    valid_responses = [r for r in session.responses if not r.error]

    responses_text = ""
    for i, resp in enumerate(valid_responses):
        responses_text += f"\n\n--- {resp.model_name} ---\n{resp.response}"

    reviews_text = ""
    for review in session.peer_reviews:
        reviews_text += f"\n\n--- Review by {review.reviewer_model} ---\n{json.dumps(review.rankings, indent=2)}"

    synthesis_prompt = f"""You are Grok, the Chairman of a council of AI models. Your job is to give the final verdict based on the council's responses.

Original Question: {session.question}

Council Responses:
{responses_text}

Peer Reviews (rankings from each model):
{reviews_text}

Based on all the responses and peer reviews:
1. Summarize what the council members said
2. State which response(s) you agree with most and why
3. Give YOUR final opinion/answer to the original question

Be direct and decisive. Do NOT ask follow-up questions. Give a clear final answer."""

    try:
        logger.info(f"Starting synthesis with {CHAIRMAN_MODEL['name']}")
        logger.info(f"Synthesis prompt length: {len(synthesis_prompt)} chars")

        final_response = await openrouter_client.chat(
            model_id=CHAIRMAN_MODEL["id"],
            prompt=synthesis_prompt,
            system_prompt="You are the Chairman of an AI council. Synthesize the collective wisdom into a clear, authoritative final answer.",
            max_tokens=4096
        )

        logger.info(f"Synthesis complete, response length: {len(final_response)} chars")

        session.final_synthesis = final_response
        session.status = "synthesized"

        return SessionResponse(
            session=session,
            message="Synthesis complete!"
        )
    except Exception as e:
        logger.error(f"Synthesis failed: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


@app.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get the current state of a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session=sessions[session_id],
        message="Session retrieved"
    )


@app.post("/session/{session_id}/run-all", response_model=SessionResponse)
async def run_full_council(session_id: str):
    """Run the full council process: responses -> reviews -> synthesis."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    # Step 1: Get responses
    if session.status == "pending":
        await get_council_responses(session_id)

    # Step 2: Get peer reviews
    if session.status == "responses_complete":
        await get_peer_reviews(session_id)

    # Step 3: Synthesize
    if session.status == "reviews_complete":
        await synthesize_response(session_id)

    return SessionResponse(
        session=sessions[session_id],
        message="Full council process complete!"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
