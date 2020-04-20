from typing import Union

from sqlalchemy import Column, BigInteger, Integer

from database import db


class HelperRoles(db.Base):
    __tablename__ = "helper_roles"

    role_id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    score: Union[Column, int] = Column(Integer)

    @staticmethod
    def create(role_id: int, score: int) -> "HelperRoles":
        roles: HelperRoles = HelperRoles(role_id=role_id, score=score)
        
        db.add(roles)

        return roles

    @staticmethod
    def get(role_id: int) -> "HelperRoles":
        if (row := db.get(HelperRoles, role_id)) is None:
            return HelperRoles.create(role_id, 0)

        return row

    @staticmethod
    def set(role_id: int, score: int) -> "HelperRoles":
        if (row := db.get(HelperRoles, role_id)) is None:
            return HelperRoles.create(role_id, score)

        row.score = score
        return row

    @staticmethod
    def remove(role_id: int) -> bool:
        if (row := db.get(HelperRoles, role_id)) is None:
            return False

        row.delete()
        return True

    @staticmethod
    def all() -> "HelperRoles":
        return db.all(HelperRoles)