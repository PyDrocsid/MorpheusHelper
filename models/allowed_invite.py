from datetime import datetime
from typing import Union

from sqlalchemy import Column, String, BigInteger, DateTime

from database import db


class AllowedInvite(db.Base):
    __tablename__ = "allowed_invite"

    guild_id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    code: Union[Column, str] = Column(String(16))
    guild_name: Union[Column, str] = Column(String(128))
    applicant: Union[Column, int] = Column(BigInteger)
    approver: Union[Column, int] = Column(BigInteger)
    created_at: Union[Column, datetime] = Column(DateTime)

    @staticmethod
    def create(guild_id: int, code: str, guild_name: str, applicant: int, approver: int) -> "AllowedInvite":
        row = AllowedInvite(
            guild_id=guild_id,
            code=code,
            guild_name=guild_name,
            applicant=applicant,
            approver=approver,
            created_at=datetime.utcnow(),
        )
        db.add(row)
        return row
