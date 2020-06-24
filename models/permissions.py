from typing import Union

from sqlalchemy import Column, String, Integer

from database import db


class PermissionModel(db.Base):
    __tablename__ = "permissions"

    permission: Union[Column, str] = Column(String(64), primary_key=True, unique=True)
    level: Union[Column, int] = Column(Integer)

    @staticmethod
    def create(permission: str, level: int) -> "PermissionModel":
        row = PermissionModel(permission=permission, level=level)
        db.add(row)
        return row

    @staticmethod
    def get(permission: str) -> int:
        if (row := db.get(PermissionModel, permission)) is None:
            from util import ADMINISTRATOR

            row = PermissionModel.create(permission, ADMINISTRATOR)

        return row.level

    @staticmethod
    def set(permission: str, level: int) -> "PermissionModel":
        if (row := db.get(PermissionModel, permission)) is None:
            return PermissionModel.create(permission, level)

        row.level = level
        return row
