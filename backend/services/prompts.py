from typing import List

from schemas import ModelResponse


class Prompts:
    """Centralized prompt templates for the LLM Council."""

    COUNCIL_MEMBER_SYSTEM = (
        "You are a helpful assistant participating in a council of AI models. "
        "Provide a direct, thoughtful, and concise answer to the user's question. "
        "Do NOT ask follow-up questions. Do NOT ask for clarification. "
        "Just give your best answer based on the question asked."
    )

    CHAIRMAN_SYSTEM = (
        "You are the Chairman of an AI council. "
        "Synthesize the collective wisdom into a clear, authoritative final answer."
    )

    @staticmethod
    def build_review_prompt(
            question: str,
            valid_responses: List[ModelResponse],
            reviewer_id: str
    ) -> str:
        """Build the peer review prompt for a council member."""
        responses_text = ""
        for i, resp in enumerate(valid_responses):
            if resp.model_id != reviewer_id:
                responses_text += f"\n\n--- Response {i + 1} ---\n{resp.response}"

        return f"""You are reviewing responses from other AI models to the following question:

Question: {question}

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

    @staticmethod
    def build_synthesis_prompt(
            question: str,
            valid_responses: List[ModelResponse],
            reviews_text: str
    ) -> str:
        """Build the synthesis prompt for the chairman."""
        responses_text = ""
        for resp in valid_responses:
            responses_text += f"\n\n--- {resp.model_name} ---\n{resp.response}"

        return f"""You are Grok, the Chairman of a council of AI models. Your job is to give the final verdict based on the council's responses.

Original Question: {question}

Council Responses:
{responses_text}

Peer Reviews (rankings from each model):
{reviews_text}

Based on all the responses and peer reviews:
1. Summarize what the council members said
2. State which response(s) you agree with most and why
3. Give YOUR final opinion/answer to the original question

Be direct and decisive. Do NOT ask follow-up questions. Give a clear final answer."""
