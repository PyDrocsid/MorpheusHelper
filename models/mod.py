from datetime import datetime
from typing import Union

from sqlalchemy import Column, Integer, BigInteger, DateTime, Text, Boolean

from database import db


class Report(db.Base):
    __tablename__ = "report"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8_bin"))
    reporter: Union[Column, int] = Column(BigInteger)
    timestamp: Union[Column, datetime] = Column(DateTime)
    reason: Union[Column, str] = Column(Text(collation="utf8_bin"))

    @staticmethod
    def create(member: int, member_name: str, reporter: int, reason: str) -> "Report":
        row = Report(member=member, member_name=member_name, reporter=reporter, timestamp=datetime.now(), reason=reason)
        db.add(row)
        return row


class Warn(db.Base):
    __tablename__ = "warn"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8_bin"))
    mod: Union[Column, int] = Column(BigInteger)
    timestamp: Union[Column, datetime] = Column(DateTime)
    reason: Union[Column, str] = Column(Text(collation="utf8_bin"))

    @staticmethod
    def create(member: int, member_name: str, mod: int, reason: str) -> "Warn":
        row = Warn(member=member, member_name=member_name, mod=mod, timestamp=datetime.now(), reason=reason)
        db.add(row)
        return row


class Mute(db.Base):
    __tablename__ = "mute"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8_bin"))
    mod: Union[Column, int] = Column(BigInteger)
    timestamp: Union[Column, datetime] = Column(DateTime)
    days: Union[Column, int] = Column(Integer)
    reason: Union[Column, str] = Column(Text(collation="utf8_bin"))
    active: Union[Column, bool] = Column(Boolean)

    @staticmethod
    def create(member: int, member_name: str, mod: int, days: int, reason: str) -> "Mute":
        row = Mute(
            member=member,
            member_name=member_name,
            mod=mod,
            timestamp=datetime.now(),
            days=days,
            reason=reason,
            active=True,
        )
        db.add(row)
        return row

    @staticmethod
    def deactivate(mute_id: int):
        row = db.get(Mute, mute_id)
        row.active = False


class Kick(db.Base):
    __tablename__ = "kick"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8_bin"))
    mod: Union[Column, int] = Column(BigInteger)
    timestamp: Union[Column, datetime] = Column(DateTime)
    reason: Union[Column, str] = Column(Text(collation="utf8_bin"))

    @staticmethod
    def create(member: int, member_name: str, mod: int, reason: str) -> "Kick":
        row = Kick(member=member, member_name=member_name, mod=mod, timestamp=datetime.now(), reason=reason)
        db.add(row)
        return row


class Ban(db.Base):
    __tablename__ = "ban"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8_bin"))
    mod: Union[Column, int] = Column(BigInteger)
    timestamp: Union[Column, datetime] = Column(DateTime)
    days: Union[Column, int] = Column(Integer)
    reason: Union[Column, str] = Column(Text(collation="utf8_bin"))
    active: Union[Column, bool] = Column(Boolean)

    @staticmethod
    def create(member: int, member_name: str, mod: int, days: int, reason: str) -> "Ban":
        row = Ban(
            member=member,
            member_name=member_name,
            mod=mod,
            timestamp=datetime.now(),
            days=days,
            reason=reason,
            active=True,
        )
        db.add(row)
        return row

    @staticmethod
    def deactivate(ban_id: int):
        row = db.get(Ban, ban_id)
        row.active = False
