import asyncio
import json
from typing import List

from clients import OpenRouterClient
from config import COUNCIL_MODELS, CHAIRMAN_MODEL
from core.logging import logger
from schemas import ModelResponse, PeerReview, CouncilSession
from .prompts import Prompts


class CouncilService:
    """Service for managing LLM Council operations."""

    def __init__(self, client: OpenRouterClient):
        self.client = client

    async def get_council_responses(self, session: CouncilSession) -> List[ModelResponse]:
        """Query all council models in parallel."""

        async def query_model(model: dict) -> ModelResponse:
            try:
                response = await self.client.chat(
                    model_id=model["id"],
                    prompt=session.question,
                    system_prompt=Prompts.COUNCIL_MEMBER_SYSTEM
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

        tasks = [query_model(model) for model in COUNCIL_MODELS]
        responses = await asyncio.gather(*tasks)
        return list(responses)

    async def get_peer_reviews(self, session: CouncilSession) -> List[PeerReview]:
        """Have each council member review and rank the others' responses."""
        valid_responses = [r for r in session.responses if not r.error]

        if len(valid_responses) < 2:
            return []

        async def get_review(model: dict) -> PeerReview:
            try:
                prompt = Prompts.build_review_prompt(
                    question=session.question,
                    valid_responses=valid_responses,
                    reviewer_id=model["id"]
                )

                response = await self.client.chat(
                    model_id=model["id"],
                    prompt=prompt,
                    temperature=0.3
                )

                # Try to parse JSON from response
                try:
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

        tasks = [get_review(model) for model in COUNCIL_MODELS]
        reviews = await asyncio.gather(*tasks)
        return list(reviews)

    async def synthesize_response(self, session: CouncilSession) -> str:
        """Have the chairman synthesize a final response."""
        valid_responses = [r for r in session.responses if not r.error]

        reviews_text = ""
        for review in session.peer_reviews:
            reviews_text += f"\n\n--- Review by {review.reviewer_model} ---\n{json.dumps(review.rankings, indent=2)}"

        synthesis_prompt = Prompts.build_synthesis_prompt(
            question=session.question,
            valid_responses=valid_responses,
            reviews_text=reviews_text
        )

        logger.info(f"Starting synthesis with {CHAIRMAN_MODEL['name']}")
        logger.info(f"Synthesis prompt length: {len(synthesis_prompt)} chars")

        final_response = await self.client.chat(
            model_id=CHAIRMAN_MODEL["id"],
            prompt=synthesis_prompt,
            system_prompt=Prompts.CHAIRMAN_SYSTEM,
            max_tokens=4096
        )

        logger.info(f"Synthesis complete, response length: {len(final_response)} chars")
        return final_response
