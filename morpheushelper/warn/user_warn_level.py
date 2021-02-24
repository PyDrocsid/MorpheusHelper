from aioredis import create_redis_pool
from config.config import get_config_entry
from discord import Member

redis = await create_redis_pool(get_config_entry("REDIS_HOSTNAME") + ":" + get_config_entry("REDIS_PORT"))


def _get_redis_key(member: Member) -> str:
    return "warn_score_" + member.id


async def get_user_warn_score(member: Member) -> int:
    warn_score: int = await redis.get(_get_redis_key(member))

    if not warn_score:
        return 0

    return warn_score


async def increase_warn_score(member: Member) -> int:
    warn_score: int = await get_user_warn_score(member) + 1

    await redis.set(_get_redis_key(member), warn_score, ex=2 * 60 * 60)  # 2 hour expiration time

    return warn_score
