"""
Distributed rate limiter using Redis with fallback to in-memory.

Supports horizontal scaling across multiple API instances.
"""

import time
import logging
from typing import Optional
from fastapi import Request, HTTPException, status

from config import settings
from core.cache import get_redis_client

logger = logging.getLogger("llm-council.rate_limit")

# Fallback in-memory storage (for when Redis is unavailable)
_memory_limits: dict[str, list[float]] = {}
_last_cleanup = time.time()


class DistributedRateLimiter:
    """
    Redis-based rate limiter with sliding window algorithm.

    Features:
    - Distributed across multiple instances
    - Sliding window for accurate rate limiting
    - Automatic fallback to in-memory
    - Configurable per-client limits
    """

    def __init__(self, requests_per_window: int, window_seconds: int):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds

    def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for the client."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _memory_cleanup(self):
        """Periodic cleanup of expired entries."""
        global _last_cleanup, _memory_limits
        now = time.time()

        # Only cleanup every 5 minutes
        if now - _last_cleanup < 300:
            return

        cutoff = now - self.window_seconds
        for client_id in list(_memory_limits.keys()):
            _memory_limits[client_id] = [
                t for t in _memory_limits[client_id] if t > cutoff
            ]
            if not _memory_limits[client_id]:
                del _memory_limits[client_id]

        _last_cleanup = now

    def _check_redis(self, client_id: str, now: float) -> tuple[bool, Optional[int]]:
        """Check rate limit using Redis."""
        redis_client = get_redis_client()
        if redis_client is None:
            return None, None  # Signal fallback to memory

        try:
            key = f"rate_limit:{client_id}"
            pipe = redis_client.pipeline()

            # Remove old entries
            cutoff = now - self.window_seconds
            pipe.zremrangebyscore(key, 0, cutoff)

            # Count current requests
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now): now})

            # Set expiry
            pipe.expire(key, self.window_seconds + 10)

            results = pipe.execute()
            current_count = results[1]  # Result of zcard

            if current_count < self.requests_per_window:
                return True, None
            else:
                # Get oldest request time for retry-after calculation
                oldest = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    retry_after = int(oldest_time + self.window_seconds - now) + 1
                    return False, retry_after
                return False, self.window_seconds

        except Exception as e:
            logger.warning(
                f"Redis rate limit check failed: {e}. Falling back to memory."
            )
            return None, None  # Fallback to memory

    def _check_memory(self, client_id: str, now: float) -> tuple[bool, Optional[int]]:
        """Check rate limit using in-memory storage (fallback)."""
        global _memory_limits

        self._memory_cleanup()

        # Initialize if needed
        if client_id not in _memory_limits:
            _memory_limits[client_id] = []

        # Remove old requests
        cutoff = now - self.window_seconds
        _memory_limits[client_id] = [t for t in _memory_limits[client_id] if t > cutoff]

        # Check limit
        if len(_memory_limits[client_id]) < self.requests_per_window:
            _memory_limits[client_id].append(now)
            return True, None
        else:
            # Calculate retry-after
            oldest = min(_memory_limits[client_id])
            retry_after = int(oldest + self.window_seconds - now) + 1
            return False, retry_after

    def is_allowed(self, request: Request) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed.

        Returns:
            (is_allowed, retry_after_seconds)
        """
        # Skip if rate limiting is disabled
        if self.requests_per_window <= 0:
            return True, None

        client_id = self._get_client_id(request)
        now = time.time()

        # Try Redis first
        allowed, retry_after = self._check_redis(client_id, now)

        # Fallback to memory if Redis failed
        if allowed is None:
            allowed, retry_after = self._check_memory(client_id, now)

        return allowed, retry_after

    def get_remaining(self, request: Request) -> int:
        """Get remaining requests in current window."""
        client_id = self._get_client_id(request)
        now = time.time()

        redis_client = get_redis_client()
        if redis_client is not None:
            try:
                key = f"rate_limit:{client_id}"
                cutoff = now - self.window_seconds
                redis_client.zremrangebyscore(key, 0, cutoff)
                current_count = redis_client.zcard(key)
                return max(0, self.requests_per_window - current_count)
            except Exception:
                pass

        # Fallback to memory
        if client_id in _memory_limits:
            cutoff = now - self.window_seconds
            _memory_limits[client_id] = [
                t for t in _memory_limits[client_id] if t > cutoff
            ]
            return max(0, self.requests_per_window - len(_memory_limits[client_id]))

        return self.requests_per_window


# Global distributed rate limiter instance
distributed_rate_limiter = DistributedRateLimiter(
    requests_per_window=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window,
)


async def check_distributed_rate_limit(request: Request) -> None:
    """
    FastAPI dependency to check distributed rate limit.

    Usage:
        @router.post("/endpoint")
        async def endpoint(_rate_limit: None = Depends(check_distributed_rate_limit)):
            ...
    """
    is_allowed, retry_after = distributed_rate_limiter.is_allowed(request)

    if not is_allowed:
        remaining = distributed_rate_limiter.get_remaining(request)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds. Remaining: {remaining}",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Remaining": str(remaining),
            },
        )
