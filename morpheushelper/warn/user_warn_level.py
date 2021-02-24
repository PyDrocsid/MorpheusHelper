from redis import Redis
from config.config import get_config_entry
from discord import Member

redis = Redis(host=get_config_entry("REDIS_HOSTNAME"), port=get_config_entry("REDIS_PORT"))


def _get_redis_key(member: Member) -> str:
    return "warn_lvl_" + member.id


def get_user_warn_score(member: Member) -> int:
    warn_score: int = redis.get(_get_redis_key(member))

    if not warn_score:
        return 0

    return warn_score


def increase_warn_score(member: Member) -> int:
    warn_score: int = get_user_warn_score(member) + 1

    redis.set(_get_redis_key(member), warn_score + warn_score, ex=2 * 60 * 60)  # 2 hour expiration time

    return warn_score
