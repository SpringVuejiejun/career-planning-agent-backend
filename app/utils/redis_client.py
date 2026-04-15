import redis.asyncio as redis
from typing import Optional

_redis_client: Optional[redis.Redis] = None

async def init_redis(redis_url: str):
    global _redis_client
    _redis_client = await redis.from_url(redis_url, decode_responses=True)
    return _redis_client

async def get_redis() -> redis.Redis:
    return _redis_client

async def close_redis():
    if _redis_client:
        await _redis_client.close()