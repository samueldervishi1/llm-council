from fastapi import APIRouter

from config import COUNCIL_MODELS, CHAIRMAN_MODEL

router = APIRouter(tags=["models"])


@router.get("/models")
async def get_models():
    """Get the configured council models and chairman."""
    return {
        "council_models": COUNCIL_MODELS,
        "chairman_model": CHAIRMAN_MODEL
    }
