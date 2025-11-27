import asyncio
import json
from statistics import mean, stdev
from typing import List, Optional, Dict

from clients import OpenRouterClient
from config import COUNCIL_MODELS, CHAIRMAN_MODEL
from core.logging import logger
from schemas import ModelResponse, PeerReview, ConversationRound
from .prompts import Prompts


def analyze_disagreement(
        responses: List[ModelResponse],
        peer_reviews: List[PeerReview]
) -> List[Dict]:
    """
    Analyze disagreement among council members based on peer reviews.

    Returns a list of disagreement analysis for each response, containing:
    - model_id: The model whose response was analyzed
    - model_name: Human-readable model name
    - ranks_received: All ranks given by reviewers
    - mean_rank: Average rank
    - disagreement_score: 0 (consensus) to 1 (high disagreement)
    - has_disagreement: Whether significant disagreement exists
    """
    if not peer_reviews or not responses:
        return []

    valid_responses = [r for r in responses if not r.error]
    if len(valid_responses) < 2:
        return []

    # Map response index (1-based) to model info
    response_map = {
        i + 1: {"model_id": r.model_id, "model_name": r.model_name}
        for i, r in enumerate(valid_responses)
    }

    # Collect ranks for each response
    ranks_by_response: Dict[int, List[int]] = {i: [] for i in response_map.keys()}

    for review in peer_reviews:
        for ranking in review.rankings:
            if isinstance(ranking, dict) and "response_num" in ranking and "rank" in ranking:
                resp_num = ranking.get("response_num")
                rank = ranking.get("rank")
                if resp_num in ranks_by_response and isinstance(rank, (int, float)):
                    ranks_by_response[resp_num].append(int(rank))

    # Calculate disagreement for each response
    analysis = []
    num_responses = len(valid_responses)

    for resp_num, ranks in ranks_by_response.items():
        model_info = response_map.get(resp_num, {})

        if len(ranks) < 2:
            # Not enough data to calculate disagreement
            analysis.append({
                "model_id": model_info.get("model_id", ""),
                "model_name": model_info.get("model_name", ""),
                "ranks_received": ranks,
                "mean_rank": ranks[0] if ranks else 0,
                "disagreement_score": 0.0,
                "has_disagreement": False
            })
            continue

        avg_rank = mean(ranks)

        # Calculate standard deviation
        try:
            std = stdev(ranks)
        except:
            std = 0.0

        # Normalize disagreement score (0-1)
        # Max possible stdev for ranks 1 to N is approximately (N-1)/2
        max_std = (num_responses - 1) / 2
        disagreement_score = min(std / max_std, 1.0) if max_std > 0 else 0.0

        # Consider high disagreement if score > 0.5 or if ranks span more than half the range
        rank_range = max(ranks) - min(ranks) if ranks else 0
        has_disagreement = disagreement_score > 0.5 or rank_range >= num_responses / 2

        analysis.append({
            "model_id": model_info.get("model_id", ""),
            "model_name": model_info.get("model_name", ""),
            "ranks_received": ranks,
            "mean_rank": round(avg_rank, 2),
            "disagreement_score": round(disagreement_score, 2),
            "has_disagreement": has_disagreement
        })

    return analysis


class CouncilService:
    """Service for managing LLM Council operations."""

    def __init__(self, client: OpenRouterClient):
        self.client = client

    async def get_council_responses(
            self,
            current_round: ConversationRound,
            previous_rounds: Optional[List[ConversationRound]] = None
    ) -> List[ModelResponse]:
        """Query all council models in parallel."""
        has_context = previous_rounds and len(previous_rounds) > 0
        system_prompt = (
            Prompts.COUNCIL_MEMBER_SYSTEM_WITH_CONTEXT if has_context
            else Prompts.COUNCIL_MEMBER_SYSTEM
        )

        prompt = Prompts.build_question_with_context(
            question=current_round.question,
            previous_rounds=previous_rounds
        )

        async def query_model(model: dict) -> ModelResponse:
            try:
                response = await self.client.chat(
                    model_id=model["id"],
                    prompt=prompt,
                    system_prompt=system_prompt
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

    async def get_peer_reviews(
            self,
            current_round: ConversationRound,
            previous_rounds: Optional[List[ConversationRound]] = None
    ) -> List[PeerReview]:
        """Have each council member review and rank the others' responses."""
        valid_responses = [r for r in current_round.responses if not r.error]

        if len(valid_responses) < 2:
            return []

        async def get_review(model: dict) -> PeerReview:
            try:
                prompt = Prompts.build_review_prompt(
                    question=current_round.question,
                    valid_responses=valid_responses,
                    reviewer_id=model["id"],
                    previous_rounds=previous_rounds
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

    async def synthesize_response(
            self,
            current_round: ConversationRound,
            previous_rounds: Optional[List[ConversationRound]] = None
    ) -> str:
        """Have the chairman synthesize a final response."""
        valid_responses = [r for r in current_round.responses if not r.error]

        reviews_text = ""
        for review in current_round.peer_reviews:
            reviews_text += f"\n\n--- Review by {review.reviewer_model} ---\n{json.dumps(review.rankings, indent=2)}"

        synthesis_prompt = Prompts.build_synthesis_prompt(
            question=current_round.question,
            valid_responses=valid_responses,
            reviews_text=reviews_text,
            previous_rounds=previous_rounds
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
