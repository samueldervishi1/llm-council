import time
from collections import defaultdict
from typing import Optional

from fastapi import Request, HTTPException, status

from config import settings


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    For production with multiple workers, consider using Redis.
    """

    def __init__(self, requests_per_window: int, window_seconds: int):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for the client."""
        # Use X-Forwarded-For if behind a proxy, otherwise use client host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain (original client)
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_old_requests(self, client_id: str, current_time: float) -> None:
        """Remove requests outside the current window."""
        cutoff = current_time - self.window_seconds
        self.requests[client_id] = [
            t for t in self.requests[client_id] if t > cutoff
        ]

    def is_allowed(self, request: Request) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed.

        Returns:
            (is_allowed, retry_after_seconds)
        """
        # Skip rate limiting if not configured
        if self.requests_per_window <= 0:
            return True, None

        client_id = self._get_client_id(request)
        current_time = time.time()

        # Cleanup old requests
        self._cleanup_old_requests(client_id, current_time)

        # Check if under limit
        if len(self.requests[client_id]) < self.requests_per_window:
            self.requests[client_id].append(current_time)
            return True, None

        # Calculate retry-after
        oldest_request = min(self.requests[client_id])
        retry_after = int(oldest_request + self.window_seconds - current_time) + 1

        return False, retry_after

    def get_remaining(self, request: Request) -> int:
        """Get remaining requests in current window."""
        client_id = self._get_client_id(request)
        current_time = time.time()
        self._cleanup_old_requests(client_id, current_time)
        return max(0, self.requests_per_window - len(self.requests[client_id]))


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests_per_window=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window
)


async def check_rate_limit(request: Request) -> None:
    """
    Dependency to check rate limit.

    Usage:
        @router.post("/endpoint")
        async def endpoint(request: Request, _rate_limit: None = Depends(check_rate_limit)):
            ...
    """
    is_allowed, retry_after = rate_limiter.is_allowed(request)

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )
