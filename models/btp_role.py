from typing import Union

from sqlalchemy import Column, BigInteger

from PyDrocsid.database import db


class BTPRole(db.Base):
    __tablename__ = "btp_role"

    role_id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)

    @staticmethod
    def create(role_id: int) -> "BTPRole":
        row = BTPRole(role_id=role_id)
        db.add(row)
        return row
