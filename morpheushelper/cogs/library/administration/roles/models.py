from __future__ import annotations

from typing import Union, List

from sqlalchemy import Column, BigInteger

from PyDrocsid.database import db


class RoleAuth(db.Base):
    __tablename__ = "role_auth"

    source: Union[Column, int] = Column(BigInteger, primary_key=True)
    target: Union[Column, int] = Column(BigInteger, primary_key=True)

    @staticmethod
    def add(source: int, target: int):
        db.add(RoleAuth(source=source, target=target))

    @staticmethod
    def check(source: int, target: int) -> bool:
        return db.first(RoleAuth, source=source, target=target) is not None

    @staticmethod
    def all(**kwargs) -> List[RoleAuth]:
        return db.all(RoleAuth, **kwargs)

    @staticmethod
    def remove(source: int, target: int):
        db.delete(db.first(RoleAuth, source=source, target=target))
