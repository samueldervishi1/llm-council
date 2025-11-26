from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    openrouter_api_key: str = ""

    # OpenRouter base URL
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    class Config:
        env_file = ".env"


settings = Settings()

# Council member models (free OpenRouter models - different providers to avoid upstream limits)
COUNCIL_MODELS = [
    {
        "id": "nvidia/nemotron-nano-9b-v2:free",
        "name": "NVIDIA Nemotron 9B",
        "provider": "openrouter"
    },
    {
        "id": "google/gemini-2.0-flash-exp:free",
        "name": "Gemini 2.0 Flash",
        "provider": "openrouter"
    },
    {
        "id": "google/gemma-3-27b-it:free",
        "name": "Gemma 3 27B",
        "provider": "openrouter"
    },
    {
        "id": "openai/gpt-oss-20b:free",
        "name": "GPT OSS 20B",
        "provider": "openrouter"
    },
]

# Chairman model (Grok 4.1 Fast via OpenRouter)
CHAIRMAN_MODEL = {
    "id": "x-ai/grok-4.1-fast:free",
    "name": "Grok 4.1 Fast",
    "provider": "openrouter"
}
