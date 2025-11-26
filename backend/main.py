from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import COUNCIL_MODELS, CHAIRMAN_MODEL, settings
from core import setup_logging
from core.dependencies import get_session_repository
from db import get_database, close_database
from routers import sessions_router, models_router
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


app = FastAPI(
    title="LLM Council API",
    description="Query multiple LLMs and synthesize their responses",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions_router)
app.include_router(models_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "LLM Council API", "status": "running"}


# Legacy endpoint for frontend compatibility
@app.post("/query", response_model=SessionResponse)
async def query(request: QueryRequest):
    """Start a new council session (legacy endpoint)."""
    repo = await get_session_repository()
    return await create_session(request, repo)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
