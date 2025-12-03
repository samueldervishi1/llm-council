from typing import List, Optional

from schemas import ModelResponse, ConversationRound, ChatMessage


class Prompts:
    """Centralized prompt templates for the LLM Council."""

    # ==================== FORMAL MODE PROMPTS ====================
    COUNCIL_MEMBER_SYSTEM = (
        "You are a helpful assistant participating in a council of AI models. "
        "Provide a direct, thoughtful, and concise answer to the user's question. "
        "Do NOT ask follow-up questions. Do NOT ask for clarification. "
        "Just give your best answer based on the question asked."
    )

    COUNCIL_MEMBER_SYSTEM_WITH_CONTEXT = (
        "You are a helpful assistant participating in a council of AI models. "
        "You are continuing an ongoing conversation. Use the previous context to provide "
        "a relevant, direct, and concise answer to the user's follow-up question. "
        "Do NOT ask follow-up questions. Do NOT ask for clarification. "
        "Just give your best answer based on the conversation context."
    )

    CHAIRMAN_SYSTEM = (
        "You are the Chairman of an AI council. "
        "Synthesize the collective wisdom into a clear, authoritative final answer."
    )

    # ==================== CHAT MODE PROMPTS ====================
    @staticmethod
    def get_chat_system_prompt(model_name: str, other_models: List[str]) -> str:
        """Generate system prompt for chat mode."""
        others = ", ".join(other_models)
        return f"""You are {model_name} in a group chat with other AI models: {others}.

This is like a WhatsApp group - respond naturally and conversationally:
- Keep responses short (2-4 sentences typically, can be longer if needed)
- Reply to specific models by name when agreeing/disagreeing (e.g., "@Gemma I agree because...")
- Build on what others said, don't just repeat the same points
- Have your own personality and opinions
- It's okay to disagree respectfully
- Be casual but helpful

DO NOT:
- Give long formal responses
- Repeat what others already said
- Ask clarifying questions to the user
- Be overly formal or robotic"""

    @staticmethod
    def get_chat_first_responder_prompt(model_name: str) -> str:
        """System prompt for the first model to respond in chat mode."""
        return f"""You are {model_name} in a group chat with other AI models.

You're the first to respond! Give your take on the user's question:
- Keep it conversational (2-4 sentences)
- Share your perspective naturally
- Leave room for others to add or disagree

DO NOT be overly formal or give a lecture."""

    @staticmethod
    def build_conversation_context(previous_rounds: List[ConversationRound]) -> str:
        """Build conversation context from previous rounds."""
        if not previous_rounds:
            return ""

        context = "=== PREVIOUS CONVERSATION ===\n"
        for i, round in enumerate(previous_rounds, 1):
            context += f"\n--- Round {i} ---\n"
            context += f"User Question: {round.question}\n"
            if round.final_synthesis:
                context += f"Council Verdict: {round.final_synthesis}\n"
        context += "\n=== END PREVIOUS CONVERSATION ===\n\n"
        return context

    @staticmethod
    def build_question_with_context(
            question: str,
            previous_rounds: Optional[List[ConversationRound]] = None
    ) -> str:
        """Build the question prompt with optional conversation context."""
        if not previous_rounds:
            return question

        context = Prompts.build_conversation_context(previous_rounds)
        return f"{context}Current Question: {question}"

    @staticmethod
    def build_review_prompt(
            question: str,
            valid_responses: List[ModelResponse],
            reviewer_id: str,
            previous_rounds: Optional[List[ConversationRound]] = None
    ) -> str:
        """Build the peer review prompt for a council member."""
        responses_text = ""
        for i, resp in enumerate(valid_responses):
            if resp.model_id != reviewer_id:
                responses_text += f"\n\n--- Response {i + 1} ---\n{resp.response}"

        context = ""
        if previous_rounds:
            context = Prompts.build_conversation_context(previous_rounds)

        return f"""{context}You are reviewing responses from other AI models to the following question:

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
            reviews_text: str,
            previous_rounds: Optional[List[ConversationRound]] = None
    ) -> str:
        """Build the synthesis prompt for the chairman."""
        responses_text = ""
        for resp in valid_responses:
            responses_text += f"\n\n--- {resp.model_name} ---\n{resp.response}"

        context = ""
        if previous_rounds:
            context = Prompts.build_conversation_context(previous_rounds)

        return f"""{context}You are Grok, the Chairman of a council of AI models. Your job is to give the final verdict based on the council's responses.

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

    @staticmethod
    def build_chat_prompt(
            question: str,
            chat_messages: List[ChatMessage],
            previous_rounds: Optional[List[ConversationRound]] = None
    ) -> str:
        """Build the prompt showing chat history for the next model to respond."""
        parts = []

        # Add previous round context if exists
        if previous_rounds:
            parts.append(Prompts.build_conversation_context(previous_rounds))

        # Add the current question
        parts.append(f"User's question: {question}\n")

        # Add chat history
        if chat_messages:
            parts.append("=== GROUP CHAT ===")
            for msg in chat_messages:
                parts.append(f"{msg.model_name}: {msg.content}")
            parts.append("=== END CHAT ===\n")
            parts.append("Now it's your turn. Respond to the conversation above.")
        else:
            parts.append("You're first to respond. Share your thoughts!")

        return "\n".join(parts)
