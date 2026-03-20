import datetime
import decimal
import hashlib
import json
import logging
import os

import redis

logger = logging.getLogger(__name__)

# Default TTL: 1 hour
# Why? Database data can change, so we don't want infinite cache
DEFAULT_TTL = int(os.getenv("CACHE_TTL", 3600))

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)

def _get_client() -> redis.Redis:
    """Creates and returns a Redis client."""
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True,  # returns strings instead of bytes
    )


def _make_key(question: str) -> str:
    """
    Converts a question into a cache key using MD5.

    Why MD5? Not for security — just to create a short, consistent key
    from any question string. Handles spaces, caps, punctuation.
    Example: "Which products have less than 20 units?" -> "cache:a3f8c2..."

    Normalizing to lowercase ensures "MacBook" and "macbook" hit the same key.
    """
    normalized = question.strip().lower()
    hash_key = hashlib.md5(normalized.encode()).hexdigest()
    return f"cache:{hash_key}"


def get(question: str) -> dict | None:
    """
    Looks up a question in the cache.
    Returns the cached result dict, or None if not found.
    """
    try:
        client = _get_client()
        key = _make_key(question)
        value = client.get(key)

        if value:
            logger.info(f"Cache HIT for key: {key}")
            return json.loads(value)

        logger.info(f"Cache MISS for key: {key}")
        return None

    except redis.RedisError as e:
        # If Redis is down, we don't want to crash the app.
        # Just log and continue without cache (graceful degradation).
        logger.warning(f"Redis error on GET: {e}. Skipping cache.")
        return None


def set(question: str, result: dict, ttl: int = DEFAULT_TTL) -> None:
    """
    Stores a result in the cache with a TTL (time-to-live).

    The result dict is serialized to JSON since Redis only stores strings.
    DataFrames are excluded — only sql, columns, rows and answer are cached.
    """
    try:
        client = _get_client()
        key = _make_key(question)

        # Exclude non-serializable objects (e.g. DataFrames)
        serializable = {
            "sql": result.get("sql"),
            "columns": result.get("columns", []),
            "rows": [[float(v) if isinstance(v, decimal.Decimal) else v for v in row] for row in result.get("rows", [])],  # convert tuples to lists
            "answer": result.get("answer", ""),
            "error": result.get("error"),
        }

        client.setex(key, ttl, json.dumps(serializable, cls=JSONEncoder))
        logger.info(f"Cache SET for key: {key} (TTL: {ttl}s)")

    except redis.RedisError as e:
        logger.warning(f"Redis error on SET: {e}. Skipping cache.")


def invalidate(question: str) -> None:
    """Manually removes a specific question from the cache."""
    try:
        client = _get_client()
        key = _make_key(question)
        client.delete(key)
        logger.info(f"Cache INVALIDATED for key: {key}")
    except redis.RedisError as e:
        logger.warning(f"Redis error on DELETE: {e}.")


def flush_all() -> None:
    """Clears the entire cache. Useful for development or when the DB changes."""
    try:
        client = _get_client()
        client.flushdb()
        logger.info("Cache fully flushed.")
    except redis.RedisError as e:
        logger.warning(f"Redis error on FLUSH: {e}.")