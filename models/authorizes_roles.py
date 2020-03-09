from typing import Union

from sqlalchemy import Column, BigInteger

from database import db


class AuthorizedRoles(db.Base):
    __tablename__ = "authorized_roles"

    server: Union[Column, int] = Column(BigInteger, primary_key=True)
    role: Union[Column, int] = Column(BigInteger, primary_key=True)

    @staticmethod
    def create(server: int, role: int) -> "AuthorizedRoles":
        auth: AuthorizedRoles = AuthorizedRoles(server=server, role=role)

        db.add(auth)

        return auth
