"""Simple in-memory cache with TTL support for dashboard endpoints"""
from functools import wraps
from typing import Any, Callable, Optional
from datetime import datetime, timedelta
import hashlib
import json


class CacheEntry:
    """Cache entry with TTL"""
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class TTLCache:
    """Time-to-live cache implementation"""
    def __init__(self):
        self._cache = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                return entry.value
            else:
                # Clean up expired entry
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int):
        """Set value in cache with TTL"""
        self._cache[key] = CacheEntry(value, ttl_seconds)

    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()

    def clear_expired(self):
        """Remove all expired entries"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]


# Global cache instance
_dashboard_cache = TTLCache()


def cache_key_from_params(**kwargs) -> str:
    """Generate cache key from function parameters"""
    # Filter out None values and db session
    params = {k: v for k, v in kwargs.items() if v is not None and k != 'db'}

    # Convert dates to strings for JSON serialization
    for key, value in params.items():
        if hasattr(value, 'isoformat'):
            params[key] = value.isoformat()

    # Create stable hash from sorted params
    params_str = json.dumps(params, sort_keys=True)
    return hashlib.md5(params_str.encode()).hexdigest()


def cached(ttl_seconds: int = 300):
    """
    Decorator to cache function results with TTL.

    Args:
        ttl_seconds: Time to live in seconds (default: 300 = 5 minutes)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{cache_key_from_params(**kwargs)}"

            # Try to get from cache
            cached_value = _dashboard_cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call original function
            result = await func(*args, **kwargs)

            # Store in cache
            _dashboard_cache.set(cache_key, result, ttl_seconds)

            return result
        return wrapper
    return decorator


def clear_dashboard_cache():
    """Clear all dashboard cache entries"""
    _dashboard_cache.clear()


def clear_expired_cache():
    """Remove expired cache entries (for periodic cleanup)"""
    _dashboard_cache.clear_expired()
