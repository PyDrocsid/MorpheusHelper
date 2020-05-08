from typing import Union

from sqlalchemy import Column, BigInteger

from database import db


class AuthorizedRole(db.Base):
    __tablename__ = "authorized_role"

    role: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)

    @staticmethod
    def create(role: int) -> "AuthorizedRole":
        auth: AuthorizedRole = AuthorizedRole(role=role)

        db.add(auth)

        return auth
