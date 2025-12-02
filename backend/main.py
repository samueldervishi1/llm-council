import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import COUNCIL_MODELS, CHAIRMAN_MODEL, settings
from core import setup_logging
from core.dependencies import get_session_repository
from db import get_database, close_database
from routers import sessions_router, models_router, shared_router
from routers.sessions import create_session
from schemas import QueryRequest, SessionResponse

# Configure logging
setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler."""
    print("LLM Council API starting...")
    print(f"Council members: {[m['name'] for m in COUNCIL_MODELS]}")
    print(f"Chairman: {CHAIRMAN_MODEL['name']}")

    # Connect to MongoDB
    print(f"Connecting to MongoDB at {settings.mongodb_url}...")
    try:
        db = await get_database()
        # Ping to verify connection
        await db.command("ping")
        print(f"MongoDB connected successfully (database: {settings.mongodb_database})")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")

    yield
    print("LLM Council API shutting down...")
    await close_database()
    print("MongoDB connection closed")


# Read version from root version.json
VERSION_FILE = Path(__file__).parent.parent / "version.json"
with open(VERSION_FILE) as f:
    VERSION = json.load(f)["version"]

DESCRIPTION = """
# LLM Council API

A powerful framework for querying multiple Large Language Models simultaneously and synthesizing their collective intelligence.

## Overview

The LLM Council enables you to:
- **Query multiple LLMs** in parallel with a single question
- **Collect peer reviews** where each model evaluates others' responses
- **Synthesize a final answer** using a chairman model that considers all perspectives

## How It Works

1. **Create a Session** - Start a new council session with your question
2. **Collect Responses** - Each council member (LLM) provides their answer
3. **Peer Review** - Models review and rank each other's responses
4. **Synthesis** - The chairman analyzes all responses and reviews to produce a final, well-rounded answer

## Quick Start

Use `/session/{id}/run-all` to execute the full council process in one call, or step through each phase individually for more control.
"""

tags_metadata = [
    {
        "name": "sessions",
        "description": "Manage council sessions - create, retrieve, delete, and run the council deliberation process.",
    },
    {
        "name": "models",
        "description": "View configured council member models and the chairman model.",
    },
]

# Disable docs in production
is_production = settings.environment == "production"

app = FastAPI(
    title="LLM Council API",
    description=DESCRIPTION,
    version=VERSION,
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact={
        "name": "LLM Council",
    },
    license_info={
        "name": "MIT",
    },
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

# CORS middleware
# Default development origins + any production origins from env
cors_origins = ["http://localhost:5173", "http://localhost:3000"]
if settings.cors_origins:
    cors_origins.extend([origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions_router)
app.include_router(models_router)
app.include_router(shared_router)


@app.get("/", tags=["health"])
async def root():
    """
    Health Check

    Returns the current status and version of the API.
    Use this endpoint to verify the API is running.
    """
    return {"message": "LLM Council API", "status": "running", "version": VERSION}


# Legacy endpoint for frontend compatibility
@app.post("/query", response_model=SessionResponse)
async def query(request: QueryRequest):
    """Start a new council session (legacy endpoint)."""
    repo = await get_session_repository()
    return await create_session(request, repo)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
