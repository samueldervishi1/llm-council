from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    openrouter_api_key: str = ""

    # OpenRouter base URL
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "llm_council"

    # CORS - comma-separated list of allowed origins for production
    cors_origins: str = ""

    # Environment - set to "production" to disable docs endpoints
    environment: str = "development"

    # API Authentication - optional API key for protecting endpoints
    # If set, requests must include X-API-Key header or api_key query param
    api_key: str = ""

    # Rate limiting
    rate_limit_requests: int = 100  # requests per minute
    rate_limit_window: int = 60  # window in seconds

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
        "id": "meta-llama/llama-3.2-3b-instruct:free",
        "name": "Llama 3.2 3B",
        "provider": "openrouter"
    },
    {
        "id": "microsoft/phi-3-mini-128k-instruct:free",
        "name": "Phi-3 Mini",
        "provider": "openrouter"
    },
    {
        "id": "openai/gpt-oss-20b:free",
        "name": "GPT OSS 20B",
        "provider": "openrouter"
    },
]

# Chairman model - using Qwen which is very stable
CHAIRMAN_MODEL = {
    "id": "qwen/qwen-2-7b-instruct:free",
    "name": "Qwen 2 7B",
    "provider": "openrouter"
}
