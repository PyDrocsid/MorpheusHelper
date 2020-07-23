from datetime import datetime
from typing import Union

from sqlalchemy import Column, Integer, BigInteger, Text, DateTime, Boolean

from database import db


class ServerInvites(db.Base):
    __tablename__ = "server_invites"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    code: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    uses: Union[Column, int] = Column(Integer)
    created_at: Union[Column, datetime] = Column(DateTime)
    is_expired: Union[Column, bool] = Column(Boolean)

    @staticmethod
    def create(member: int, member_name: str, code: str, uses: int, created_at: datetime) -> "ServerInvites":
        row = ServerInvites(
            member=member, member_name=member_name, code=code, uses=uses, created_at=created_at, is_expired=False,
        )
        db.add(row)
        return row

    @staticmethod
    def update(invite_code: str, uses: int):
        row = db.first(ServerInvites, code=invite_code)
        row.uses = uses

    @staticmethod
    def updateExpired(invite_code: str, expired: bool):
        row = db.first(ServerInvites, code=invite_code)
        row.is_expired = expired
