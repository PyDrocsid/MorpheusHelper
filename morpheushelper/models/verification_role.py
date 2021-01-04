from typing import Union

from PyDrocsid.database import db
from sqlalchemy import Column, BigInteger, Boolean


class VerificationRole(db.Base):
    __tablename__ = "verification_role"

    role_id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    reverse: Union[Column, bool] = Column(Boolean)

    @staticmethod
    def create(role_id: int, reverse: bool) -> "VerificationRole":
        row = VerificationRole(role_id=role_id, reverse=reverse)
        db.add(row)
        return row
