from collections import Counter
from os import getenv
from pathlib import Path
from subprocess import getoutput  # noqa: S404
from typing import Type, Union

import yaml
from discord import Member, User

from PyDrocsid.permission import BasePermissionLevel, BasePermission
from PyDrocsid.settings import Settings
from PyDrocsid.translations import Translations


class Contributor:
    Defelo = (370876111992913922, "MDQ6VXNlcjQxNzQ3NjA1")
    TNT2k = (212866839083089921, "MDQ6VXNlcjQ0MzQ5NzUw")
    wolflu = (339062431131369472, "MDQ6VXNlcjYwMDQ4NTY1")
    MaxiHuHe04 = (302365095688798209, "MDQ6VXNlcjEyOTEzNTE4")
    ce_phox = (306774624090456075, "MDQ6VXNlcjQwNTE2OTkx")


class Config:
    NAME: str
    VERSION: str

    REPO_OWNER: str
    REPO_NAME: str
    REPO_LINK: str
    REPO_ICON: str

    AUTHOR: Contributor
    CONTRIBUTORS: Counter[Contributor] = Counter(
        {
            Contributor.Defelo: 1000,
            Contributor.TNT2k: 100,
            Contributor.wolflu: 50,
            Contributor.MaxiHuHe04: 10,
            Contributor.ce_phox: 10,
        },
    )

    ROLES: dict[str, tuple[str, bool]]

    PERMISSION_LEVELS: Type[BasePermissionLevel]
    DEFAULT_PERMISSION_LEVEL: BasePermissionLevel
    DEFAULT_PERMISSION_OVERRIDES: dict[str, dict[str, BasePermissionLevel]] = {}
    PERMISSIONS: list[BasePermission] = []
    TEAMLER_LEVEL: BasePermissionLevel


def load_version():
    Config.VERSION = getoutput("cat VERSION 2>/dev/null || git describe").lstrip("v")


def load_config_file(path: Path):
    with path.open() as file:
        config = yaml.safe_load(file)

    Config.NAME = config["name"]

    Config.REPO_OWNER = config["repo"]["owner"]
    Config.REPO_NAME = config["repo"]["name"]
    Config.REPO_LINK = f"https://github.com/{Config.REPO_OWNER}/{Config.REPO_NAME}"
    Config.REPO_ICON = config["repo"]["icon"]

    Config.AUTHOR = getattr(Contributor, config["author"])

    if (lang := getenv("LANGUAGE", config["default_language"])) not in config["languages"]:
        raise ValueError(f"unknown language: {lang}")
    Translations.LANGUAGE = lang

    Config.ROLES = {k: (v["name"], v["check_assignable"]) for k, v in config["roles"].items()}

    permission_levels: dict[str, dict] = {
        k: v for k, v in sorted(config["permission_levels"].items(), key=lambda x: -x[1]["level"])
    }

    async def get_permission_level(cls, member: Union[Member, User]) -> BasePermissionLevel:
        if not isinstance(member, Member):
            return cls.PUBLIC

        roles = {role.id for role in member.roles}

        async def has_role(role_name):
            return await Settings.get(int, role_name + "_role") in roles

        for k, v in permission_levels.items():
            if any(getattr(member.guild_permissions, p) for p in v["if"].get("permissions", [])):
                return getattr(cls, k.upper())

            for r in v["if"].get("roles", []):
                if await has_role(r):
                    return getattr(cls, k.upper())

        return cls.PUBLIC

    Config.PERMISSION_LEVELS = BasePermissionLevel(
        "PermissionLevel",
        {
            **{k.upper(): (v["level"], v["aliases"], v["name"]) for k, v in permission_levels.items()},
            "PUBLIC": (0, ["public", "p"], "Public"),
            "OWNER": (next(iter(permission_levels.values()), {"level": 0})["level"] + 1, ["owner", "o"], "Owner"),
        },
    )
    Config.PERMISSION_LEVELS._get_permission_level = classmethod(get_permission_level)

    Config.DEFAULT_PERMISSION_LEVEL = getattr(Config.PERMISSION_LEVELS, config["default_permission_level"].upper())

    for cog, overrides in config.get("default_permission_overrides", {}).items():
        for permission, level in overrides.items():
            Config.DEFAULT_PERMISSION_OVERRIDES.setdefault(cog.lower(), {}).setdefault(
                permission.lower(),
                getattr(Config.PERMISSION_LEVELS, level.upper()),
            )

    Config.TEAMLER_LEVEL = getattr(Config.PERMISSION_LEVELS, config["teamler_level"].upper())
