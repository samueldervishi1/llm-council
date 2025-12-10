import asyncio
import json
import time
from statistics import mean, stdev, StatisticsError
from typing import List, Optional, Dict

from clients import OpenRouterClient
from config import COUNCIL_MODELS, CHAIRMAN_MODEL
from core.logging import logger
from schemas import ModelResponse, PeerReview, ConversationRound, ChatMessage
from .prompts import Prompts


def analyze_disagreement(
    responses: List[ModelResponse], peer_reviews: List[PeerReview]
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
            if (
                isinstance(ranking, dict)
                and "response_num" in ranking
                and "rank" in ranking
            ):
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
            analysis.append(
                {
                    "model_id": model_info.get("model_id", ""),
                    "model_name": model_info.get("model_name", ""),
                    "ranks_received": ranks,
                    "mean_rank": ranks[0] if ranks else 0,
                    "disagreement_score": 0.0,
                    "has_disagreement": False,
                }
            )
            continue

        avg_rank = mean(ranks)

        # Calculate standard deviation
        try:
            std = stdev(ranks)
        except StatisticsError:
            std = 0.0

        # Normalize disagreement score (0-1)
        # Max possible stdev for ranks 1 to N is approximately (N-1)/2
        max_std = (num_responses - 1) / 2
        disagreement_score = min(std / max_std, 1.0) if max_std > 0 else 0.0

        # Consider high disagreement if score > 0.5 or if ranks span more than half the range
        rank_range = max(ranks) - min(ranks) if ranks else 0
        has_disagreement = disagreement_score > 0.5 or rank_range >= num_responses / 2

        analysis.append(
            {
                "model_id": model_info.get("model_id", ""),
                "model_name": model_info.get("model_name", ""),
                "ranks_received": ranks,
                "mean_rank": round(avg_rank, 2),
                "disagreement_score": round(disagreement_score, 2),
                "has_disagreement": has_disagreement,
            }
        )

    return analysis


class CouncilService:
    """Service for managing LLM Council operations."""

    def __init__(self, client: OpenRouterClient):
        self.client = client

    def _get_active_models(
        self,
        selected_models: Optional[List[str]] = None,
        include_chairman: bool = False,
    ) -> List[dict]:
        """
        Get the models to use based on selection.

        Args:
            selected_models: List of model IDs to filter. If None, returns all council models.
            include_chairman: If True, chairman can be included (for chat mode).
                            If False, chairman is excluded even if selected (for formal mode).
        """
        if selected_models is None:
            if include_chairman:
                return COUNCIL_MODELS + [CHAIRMAN_MODEL]
            return COUNCIL_MODELS

        # Build list of available models based on mode
        if include_chairman:
            all_models = COUNCIL_MODELS + [CHAIRMAN_MODEL]
        else:
            # In formal mode, exclude chairman - they only synthesize
            all_models = COUNCIL_MODELS

        return [m for m in all_models if m["id"] in selected_models]

    async def get_council_responses(
        self,
        current_round: ConversationRound,
        previous_rounds: Optional[List[ConversationRound]] = None,
    ) -> List[ModelResponse]:
        """Query all council models in parallel."""
        has_context = previous_rounds and len(previous_rounds) > 0
        system_prompt = (
            Prompts.COUNCIL_MEMBER_SYSTEM_WITH_CONTEXT
            if has_context
            else Prompts.COUNCIL_MEMBER_SYSTEM
        )

        prompt = Prompts.build_question_with_context(
            question=current_round.question, previous_rounds=previous_rounds
        )

        async def query_model(model: dict) -> ModelResponse:
            try:
                start_time = time.monotonic()
                response = await self.client.chat(
                    model_id=model["id"], prompt=prompt, system_prompt=system_prompt
                )
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return ModelResponse(
                    model_id=model["id"],
                    model_name=model["name"],
                    response=response,
                    error=None,
                    response_time_ms=elapsed_ms,
                )
            except Exception as e:
                return ModelResponse(
                    model_id=model["id"],
                    model_name=model["name"],
                    response="",
                    error=str(e),
                    response_time_ms=None,
                )

        # Use selected models or all council models (exclude chairman in formal mode)
        active_models = self._get_active_models(
            current_round.selected_models, include_chairman=False
        )
        tasks = [query_model(model) for model in active_models]
        responses = await asyncio.gather(*tasks)
        return list(responses)

    async def get_peer_reviews(
        self,
        current_round: ConversationRound,
        previous_rounds: Optional[List[ConversationRound]] = None,
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
                    previous_rounds=previous_rounds,
                )

                response = await self.client.chat(
                    model_id=model["id"], prompt=prompt, temperature=0.3
                )

                # Try to parse JSON from response
                try:
                    start = response.find("[")
                    end = response.rfind("]") + 1
                    if start != -1 and end > start:
                        rankings = json.loads(response[start:end])
                    else:
                        rankings = []
                except json.JSONDecodeError:
                    rankings = [{"raw_response": response}]

                return PeerReview(reviewer_model=model["name"], rankings=rankings)
            except Exception as e:
                return PeerReview(
                    reviewer_model=model["name"], rankings=[{"error": str(e)}]
                )

        # Use selected models or all council models for reviews (exclude chairman)
        active_models = self._get_active_models(
            current_round.selected_models, include_chairman=False
        )
        tasks = [get_review(model) for model in active_models]
        reviews = await asyncio.gather(*tasks)
        return list(reviews)

    async def synthesize_response(
        self,
        current_round: ConversationRound,
        previous_rounds: Optional[List[ConversationRound]] = None,
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
            previous_rounds=previous_rounds,
        )

        logger.info(f"Starting synthesis with {CHAIRMAN_MODEL['name']}")
        logger.info(f"Synthesis prompt length: {len(synthesis_prompt)} chars")

        final_response = await self.client.chat(
            model_id=CHAIRMAN_MODEL["id"],
            prompt=synthesis_prompt,
            system_prompt=Prompts.CHAIRMAN_SYSTEM,
            max_tokens=4096,
        )

        logger.info(f"Synthesis complete, response length: {len(final_response)} chars")
        return final_response

    async def run_group_chat(
        self,
        current_round: ConversationRound,
        previous_rounds: Optional[List[ConversationRound]] = None,
        num_turns: int = 1,  # Default to 1 turn so user can participate
    ) -> List[ChatMessage]:
        """
        Run a group chat style discussion where models respond sequentially
        and can see/reply to each other's messages.

        Args:
            current_round: The current conversation round
            previous_rounds: Previous rounds for context
            num_turns: How many times each model should speak (default: 2)

        Returns:
            List of chat messages from all models
        """
        chat_messages: List[ChatMessage] = []

        # Use selected models or all models (council + chairman) in chat mode
        # In chat mode, chairman participates as a regular member
        all_chat_models = self._get_active_models(
            current_round.selected_models, include_chairman=True
        )

        logger.info(
            f"Starting group chat with {len(all_chat_models)} models, {num_turns} turns each"
        )

        for turn in range(num_turns):
            logger.info(f"=== Turn {turn + 1}/{num_turns} ===")

            for model in all_chat_models:
                other_models = [
                    m["name"] for m in all_chat_models if m["id"] != model["id"]
                ]

                # Build system prompt
                if not chat_messages:
                    system_prompt = Prompts.get_chat_first_responder_prompt(
                        model["name"]
                    )
                else:
                    system_prompt = Prompts.get_chat_system_prompt(
                        model["name"], other_models
                    )

                # Build user prompt with chat history
                user_prompt = Prompts.build_chat_prompt(
                    question=current_round.question,
                    chat_messages=chat_messages,
                    previous_rounds=previous_rounds,
                )

                try:
                    logger.info(f"Querying {model['name']}...")
                    start_time = time.monotonic()
                    response = await self.client.chat(
                        model_id=model["id"],
                        prompt=user_prompt,
                        system_prompt=system_prompt,
                        temperature=0.8,  # Slightly higher for more personality
                    )
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)

                    # Detect if replying to someone
                    reply_to = None
                    for other_name in other_models:
                        if f"@{other_name}" in response or other_name in response[:50]:
                            reply_to = other_name
                            break

                    message = ChatMessage(
                        model_id=model["id"],
                        model_name=model["name"],
                        content=response,
                        reply_to=reply_to,
                        response_time_ms=elapsed_ms,
                    )
                    chat_messages.append(message)
                    logger.info(f"{model['name']}: {response[:100]}...")

                except Exception as e:
                    logger.error(f"Error from {model['name']}: {e}")
                    message = ChatMessage(
                        model_id=model["id"],
                        model_name=model["name"],
                        content=f"[Failed to respond: {str(e)}]",
                        reply_to=None,
                        response_time_ms=None,
                    )
                    chat_messages.append(message)

        logger.info(f"Group chat complete with {len(chat_messages)} messages")
        return chat_messages
