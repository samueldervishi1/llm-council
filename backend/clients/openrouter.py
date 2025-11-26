import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger("llm-council.openrouter")


class OpenRouterClient:
    def __init__(self):
        self.base_url = settings.openrouter_base_url
        self.api_key = settings.openrouter_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "LLM Council"
        }

    async def chat(
            self,
            model_id: str,
            prompt: str,
            system_prompt: Optional[str] = None,
            max_tokens: int = 2048,
            temperature: float = 0.7
    ) -> str:
        """Send a chat completion request to OpenRouter."""
        logger.info(f"OpenRouter request to model: {model_id}")

        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload
            )

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"OpenRouter error for {model_id}: {response.status_code} - {error_detail}")
                raise Exception(f"OpenRouter API error ({response.status_code}): {error_detail}")

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"OpenRouter response from {model_id}: {len(content)} chars")
            return content

    async def get_available_models(self) -> list:
        """Get list of available models from OpenRouter."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/models",
                headers=self.headers
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch models: {response.text}")

            data = response.json()
            return data.get("data", [])
