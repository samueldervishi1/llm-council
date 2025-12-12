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
    rate_limit_requests: int = 100  # requests per window
    rate_limit_window: int = 60  # window in seconds

    # Redis - for caching and distributed rate limiting
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = (
        True  # Set to False to disable Redis (falls back to in-memory)
    )

    # Caching TTLs (in seconds)
    cache_ttl_sessions: int = 180  # 3 minutes for session data
    cache_ttl_models: int = 300  # 5 minutes for model list
    cache_ttl_settings: int = 60  # 1 minute for user settings

    # Circuit Breaker settings
    circuit_breaker_fail_max: int = 5  # Open circuit after 5 failures
    circuit_breaker_timeout: int = 60  # Try again after 60 seconds

    class Config:
        env_file = ".env"


settings = Settings()

# Council member models (free OpenRouter models - different providers to avoid upstream limits)
COUNCIL_MODELS = [
    {
        "id": "nvidia/nemotron-nano-9b-v2:free",
        "name": "NVIDIA Nemotron 9B",
        "provider": "openrouter",
    },
    {
        "id": "meta-llama/llama-3.2-3b-instruct:free",
        "name": "Llama 3.2 3B",
        "provider": "openrouter",
    },
    {
        "id": "mistralai/devstral-2512:free",
        "name": "Mistral Devstral 2 2512",
        "provider": "openrouter",
    },
]

# Chairman model - using GPT OSS 20B which is very stable
# Note: Chairman is separate from council members to avoid duplicate entries
CHAIRMAN_MODEL = {
    "id": "openai/gpt-oss-20b:free",
    "name": "GPT OSS 20B",
    "provider": "openrouter",
}
