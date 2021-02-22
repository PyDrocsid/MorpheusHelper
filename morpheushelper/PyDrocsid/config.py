from collections import Counter
from typing import Type, Callable

from PyDrocsid.permission import BasePermissionLevel, BasePermission


class Contributor:
    Defelo = (370876111992913922, "MDQ6VXNlcjQxNzQ3NjA1")
    TNT2k = (212866839083089921, "MDQ6VXNlcjQ0MzQ5NzUw")
    wolflu = (339062431131369472, "MDQ6VXNlcjYwMDQ4NTY1")
    MaxiHuHe04 = (302365095688798209, "MDQ6VXNlcjEyOTEzNTE4")
    ce_phox = (306774624090456075, "MDQ6VXNlcjQwNTE2OTkx")


class Config:
    NAME: str
    VERSION: str
    REPO: str
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
        }
    )
    PERMISSION_LEVELS: Type[BasePermissionLevel]
    DEFAULT_PERMISSION_LEVEL: Callable[[BasePermission], BasePermissionLevel]
    PERMISSIONS: list[BasePermission] = []
