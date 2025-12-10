"""
Redis-based caching with fallback to in-memory cache.

Supports distributed caching for horizontal scaling with TTL-based expiration.
"""

import json
import logging
import time
from typing import Optional, Any
from functools import wraps

from config import settings

logger = logging.getLogger("llm-council.cache")

# Global cache instances
_redis_client: Optional[Any] = None
_memory_cache: dict[str, tuple[Any, float]] = {}  # {key: (value, expiry_time)}


def get_redis_client():
    """Get or create Redis client."""
    global _redis_client

    if not settings.redis_enabled:
        return None

    if _redis_client is None:
        try:
            import redis

            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # Test connection
            _redis_client.ping()
            logger.info(f"Redis connected: {settings.redis_url}")
        except ImportError:
            logger.warning("Redis library not installed. Using in-memory cache.")
            return None
        except Exception as e:
            logger.error(f"Redis connection failed: {e}. Using in-memory cache.")
            _redis_client = None

    return _redis_client


async def close_redis():
    """Close Redis connection gracefully."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            _redis_client.close()
        _redis_client = None


class Cache:
    """Unified cache interface with Redis primary and memory fallback."""

    @staticmethod
    def _serialize(value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, default=str)

    @staticmethod
    def _deserialize(value: str) -> Any:
        """Deserialize JSON string to value."""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    @staticmethod
    def _memory_cleanup():
        """Remove expired entries from memory cache."""
        global _memory_cache
        now = time.time()
        expired_keys = [k for k, (_, exp) in _memory_cache.items() if exp < now]
        for key in expired_keys:
            del _memory_cache[key]

    @staticmethod
    def get(key: str) -> Optional[Any]:
        """
        Get value from cache.

        Tries Redis first, falls back to memory cache.
        """
        redis_client = get_redis_client()

        # Try Redis first
        if redis_client is not None:
            try:
                value = redis_client.get(key)
                if value is not None:
                    return Cache._deserialize(value)
            except Exception as e:
                logger.warning(f"Redis GET failed for {key}: {e}")

        # Fallback to memory cache
        Cache._memory_cleanup()
        if key in _memory_cache:
            value, expiry = _memory_cache[key]
            if expiry > time.time():
                return value
            else:
                del _memory_cache[key]

        return None

    @staticmethod
    def set(key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache with TTL (time-to-live in seconds).

        Stores in both Redis and memory for redundancy.
        """
        redis_client = get_redis_client()

        serialized = Cache._serialize(value)

        # Try Redis first
        if redis_client is not None:
            try:
                redis_client.setex(key, ttl, serialized)
            except Exception as e:
                logger.warning(f"Redis SET failed for {key}: {e}")

        # Always store in memory as backup
        _memory_cache[key] = (value, time.time() + ttl)
        Cache._memory_cleanup()

        return True

    @staticmethod
    def delete(key: str) -> bool:
        """Delete value from cache."""
        redis_client = get_redis_client()

        deleted = False

        # Delete from Redis
        if redis_client is not None:
            try:
                redis_client.delete(key)
                deleted = True
            except Exception as e:
                logger.warning(f"Redis DELETE failed for {key}: {e}")

        # Delete from memory
        if key in _memory_cache:
            del _memory_cache[key]
            deleted = True

        return deleted

    @staticmethod
    def invalidate_pattern(pattern: str):
        """
        Invalidate all keys matching a pattern (e.g., "session:*").

        Note: Pattern matching only works with Redis. Memory cache is cleared entirely.
        """
        redis_client = get_redis_client()

        if redis_client is not None:
            try:
                keys = redis_client.keys(pattern)
                if keys:
                    redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} keys matching {pattern}")
            except Exception as e:
                logger.warning(f"Redis pattern delete failed: {e}")

        # For memory cache, we clear everything (no pattern matching)
        global _memory_cache
        _memory_cache.clear()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results.

    Usage:
        @cached(ttl=180, key_prefix="session")
        async def get_session(session_id: str):
            # Expensive operation
            return session_data

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache key
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            arg_str = "_".join(str(arg) for arg in args) + "_".join(
                f"{k}={v}" for k, v in kwargs.items()
            )
            cache_key = f"{key_prefix}:{func.__name__}:{arg_str}"

            # Try to get from cache
            cached_value = Cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_value

            # Cache miss - call function
            logger.debug(f"Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)

            # Store in cache
            if result is not None:
                Cache.set(cache_key, result, ttl=ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            arg_str = "_".join(str(arg) for arg in args) + "_".join(
                f"{k}={v}" for k, v in kwargs.items()
            )
            cache_key = f"{key_prefix}:{func.__name__}:{arg_str}"

            cached_value = Cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_value

            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)

            if result is not None:
                Cache.set(cache_key, result, ttl=ttl)

            return result

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
