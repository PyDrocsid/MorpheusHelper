from __future__ import annotations

from contextvars import ContextVar
from enum import Enum
from typing import Union

from discord import Member, User
from discord.ext.commands import check, Context, CheckFailure
from sqlalchemy import Column, String, Integer

from PyDrocsid.database import db, db_thread
from PyDrocsid.translations import t

permission_override: ContextVar[BasePermissionLevel] = ContextVar("permission_override")


class PermissionModel(db.Base):
    __tablename__ = "permissions"

    permission: Union[Column, str] = Column(String(64), primary_key=True, unique=True)
    level: Union[Column, int] = Column(Integer)

    @staticmethod
    def create(permission: str, level: int) -> PermissionModel:
        row = PermissionModel(permission=permission, level=level)
        db.add(row)
        return row

    @staticmethod
    def get(permission: str, default: int) -> int:
        if (row := db.get(PermissionModel, permission)) is None:
            row = PermissionModel.create(permission, default)

        return row.level

    @staticmethod
    def set(permission: str, level: int) -> PermissionModel:
        if (row := db.get(PermissionModel, permission)) is None:
            return PermissionModel.create(permission, level)

        row.level = level
        return row


class BasePermission(Enum):
    @property
    def description(self) -> str:
        raise NotImplementedError

    @property
    def cog(self) -> str:
        return self.__class__.__name__.lower().removesuffix("permission")

    @property
    def fullname(self) -> str:
        return self.cog + "." + self.name

    @property
    def _default_level(self) -> BasePermissionLevel:
        from PyDrocsid.config import Config

        if self.cog not in Config.DEFAULT_PERMISSION_OVERRIDES:
            return Config.DEFAULT_PERMISSION_LEVEL

        return Config.DEFAULT_PERMISSION_OVERRIDES[self.cog].get(self.name, Config.DEFAULT_PERMISSION_LEVEL)

    async def resolve(self) -> BasePermissionLevel:
        from PyDrocsid.config import Config

        value: int = await db_thread(PermissionModel.get, self.fullname, self._default_level.level)
        for level in Config.PERMISSION_LEVELS:  # type: BasePermissionLevel
            if level.level == value:
                return level
        raise ValueError(f"permission level not found: {value}")

    async def set(self, level: BasePermissionLevel):
        await db_thread(PermissionModel.set, self.fullname, level.level)

    async def check_permissions(self, member: Union[Member, User]) -> bool:
        return await (await self.resolve()).check_permissions(member)

    @property
    def check(self):
        return check_permission_level(self)


class BasePermissionLevel(Enum):
    @property
    def level(self) -> int:
        return self.value[0]

    @property
    def aliases(self) -> list[str]:
        return self.value[1]

    @property
    def description(self) -> str:
        return self.value[2]

    @classmethod
    async def get_permission_level(cls, member: Union[Member, User]) -> BasePermissionLevel:
        if override := permission_override.get(None):
            return override

        return await cls._get_permission_level(member)

    @classmethod
    async def _get_permission_level(cls, member: Union[Member, User]) -> BasePermissionLevel:
        raise NotImplementedError

    async def check_permissions(self, member: Union[Member, User]) -> bool:
        level: BasePermissionLevel = await self.get_permission_level(member)
        return level.value >= self.value  # skipcq: PYL-W0143

    @property
    def check(self):
        return check_permission_level(self)

    @classmethod
    def max(cls) -> BasePermissionLevel:
        return max(cls, key=lambda x: x.level)


def check_permission_level(level: Union[BasePermission, BasePermissionLevel]):
    @check
    async def inner(ctx: Context):
        member: Union[Member, User] = ctx.author
        if not isinstance(member, Member):
            member = ctx.bot.guilds[0].get_member(ctx.author.id) or member
        if not await level.check_permissions(member):
            raise CheckFailure(t.g.not_allowed)

        return True

    return inner
