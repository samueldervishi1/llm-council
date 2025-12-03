import asyncio
import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger("llm-council.openrouter")

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # Base delay in seconds (exponential backoff)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}  # Rate limit + server errors


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

    async def _request_with_retry(
            self,
            client: httpx.AsyncClient,
            method: str,
            url: str,
            **kwargs
    ) -> httpx.Response:
        """Make HTTP request with exponential backoff retry."""
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.request(method, url, **kwargs)

                # Retry on specific status codes
                if response.status_code in RETRYABLE_STATUS_CODES:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning(
                        f"Retryable status {response.status_code}, "
                        f"attempt {attempt + 1}/{MAX_RETRIES}, waiting {delay}s"
                    )
                    await asyncio.sleep(delay)
                    continue

                return response

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_exception = e
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(
                    f"Network error: {type(e).__name__}, "
                    f"attempt {attempt + 1}/{MAX_RETRIES}, waiting {delay}s"
                )
                await asyncio.sleep(delay)

        # If we exhausted retries, raise the last exception or a generic error
        if last_exception:
            raise last_exception
        raise Exception(f"Request failed after {MAX_RETRIES} retries")

    async def chat(
            self,
            model_id: str,
            prompt: str,
            system_prompt: Optional[str] = None,
            max_tokens: int = 2048,
            temperature: float = 0.7
    ) -> str:
        """Send a chat completion request to OpenRouter with retry logic."""
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
            response = await self._request_with_retry(
                client,
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload
            )

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"OpenRouter error for {model_id}: {response.status_code} - {error_detail}")
                raise Exception(f"OpenRouter API error ({response.status_code}): {error_detail}")

            data = response.json()

            # Handle error responses that return 200 but contain error in body
            if "error" in data:
                error_msg = data["error"].get("message", str(data["error"]))
                logger.error(f"OpenRouter error for {model_id}: {error_msg}")
                raise Exception(f"Model error: {error_msg}")

            # Validate response structure
            if "choices" not in data or not data["choices"]:
                logger.error(f"Invalid response from {model_id}: {data}")
                raise Exception(f"Invalid response from model (no choices returned)")

            content = data["choices"][0]["message"]["content"]
            logger.info(f"OpenRouter response from {model_id}: {len(content)} chars")
            return content

    async def get_available_models(self) -> list:
        """Get list of available models from OpenRouter with retry logic."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await self._request_with_retry(
                client,
                "GET",
                f"{self.base_url}/models",
                headers=self.headers
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch models: {response.text}")

            data = response.json()
            return data.get("data", [])
