from datetime import datetime
from typing import Union

from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, Integer

from PyDrocsid.database import db


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

    @staticmethod
    def update(guild_id: int, code: str, guild_name: str):
        row: AllowedInvite = db.get(AllowedInvite, guild_id)
        row.code = code
        row.guild_name = guild_name


class InviteLog(db.Base):
    __tablename__ = "invite_log"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    guild_id: Union[Column, int] = Column(BigInteger)
    guild_name: Union[Column, str] = Column(String(128))
    applicant: Union[Column, int] = Column(BigInteger)
    mod: Union[Column, int] = Column(BigInteger)
    timestamp: Union[Column, datetime] = Column(DateTime)
    approved: Union[Column, bool] = Column(Boolean)

    @staticmethod
    def create(guild_id: int, guild_name: str, applicant: int, mod: int, approved: bool) -> "InviteLog":
        row = InviteLog(
            guild_id=guild_id,
            guild_name=guild_name,
            applicant=applicant,
            mod=mod,
            timestamp=datetime.utcnow(),
            approved=approved,
        )
        db.add(row)
        return row
