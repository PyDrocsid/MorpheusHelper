from typing import Union

from sqlalchemy import Column, BigInteger, String

from database import db


class Server(db.Base):
    __tablename__ = "server"

    server: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    prefix: Union[Column, str] = Column(String(16))

    @staticmethod
    def create(server: int, prefix: str) -> "Server":
        srv = Server(server=server, prefix=prefix)

        db.add(srv)

        return srv
