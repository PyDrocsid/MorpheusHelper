from datetime import datetime, timedelta
from typing import Union, Optional

from PyDrocsid.database import db
from sqlalchemy import Column, Integer, BigInteger, DateTime, Text, Boolean


class Join(db.Base):
    __tablename__ = "join"
    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    timestamp: Union[Column, datetime] = Column(DateTime)

    @staticmethod
    def create(member: int, member_name: str, timestamp: Optional[datetime] = None) -> "Join":
        row = Join(member=member, member_name=member_name, timestamp=timestamp or datetime.utcnow())
        db.add(row)
        return row

    @staticmethod
    def update(member: int, member_name: str, joined_at: datetime):
        for join in db.query(Join, member=member):
            if join.timestamp >= joined_at - timedelta(minutes=1):
                break
        else:
            Join.create(member, member_name, joined_at)


class Leave(db.Base):
    __tablename__ = "leave"
    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    timestamp: Union[Column, datetime] = Column(DateTime)

    @staticmethod
    def create(member: int, member_name: str) -> "Leave":
        row = Leave(member=member, member_name=member_name, timestamp=datetime.utcnow())
        db.add(row)
        return row


class UsernameUpdate(db.Base):
    __tablename__ = "username_update"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    new_name: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    nick: Union[Column, bool] = Column(Boolean)
    timestamp: Union[Column, datetime] = Column(DateTime)

    @staticmethod
    def create(member: int, member_name: str, new_name: str, nick: bool) -> "UsernameUpdate":
        row = UsernameUpdate(
            member=member,
            member_name=member_name,
            new_name=new_name,
            nick=nick,
            timestamp=datetime.utcnow(),
        )
        db.add(row)
        return row


class Report(db.Base):
    __tablename__ = "report"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    reporter: Union[Column, int] = Column(BigInteger)
    timestamp: Union[Column, datetime] = Column(DateTime)
    reason: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))

    @staticmethod
    def create(member: int, member_name: str, reporter: int, reason: str) -> "Report":
        row = Report(
            member=member,
            member_name=member_name,
            reporter=reporter,
            timestamp=datetime.utcnow(),
            reason=reason,
        )
        db.add(row)
        return row


class Warn(db.Base):
    __tablename__ = "warn"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    mod: Union[Column, int] = Column(BigInteger)
    timestamp: Union[Column, datetime] = Column(DateTime)
    reason: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))

    @staticmethod
    def create(member: int, member_name: str, mod: int, reason: str) -> "Warn":
        row = Warn(member=member, member_name=member_name, mod=mod, timestamp=datetime.utcnow(), reason=reason)
        db.add(row)
        return row


class Mute(db.Base):
    __tablename__ = "mute"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    mod: Union[Column, int] = Column(BigInteger)
    timestamp: Union[Column, datetime] = Column(DateTime)
    days: Union[Column, int] = Column(Integer)
    reason: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    active: Union[Column, bool] = Column(Boolean)
    deactivation_timestamp: Union[Column, Optional[datetime]] = Column(DateTime, nullable=True)
    unmute_mod: Union[Column, Optional[int]] = Column(BigInteger, nullable=True)
    unmute_reason: Union[Column, Optional[str]] = Column(Text(collation="utf8mb4_bin"), nullable=True)
    upgraded: Union[Column, bool] = Column(Boolean, default=False)
    is_upgrade: Union[Column, bool] = Column(Boolean)

    @staticmethod
    def create(member: int, member_name: str, mod: int, days: int, reason: str, is_upgrade: bool = False) -> "Mute":
        row = Mute(
            member=member,
            member_name=member_name,
            mod=mod,
            timestamp=datetime.utcnow(),
            days=days,
            reason=reason,
            active=True,
            deactivation_timestamp=None,
            unmute_mod=None,
            unmute_reason=None,
            is_upgrade=is_upgrade,
        )
        db.add(row)
        return row

    @staticmethod
    def deactivate(mute_id: int, unmute_mod: int = None, reason: str = None) -> "Mute":
        row: Mute = db.get(Mute, mute_id)
        row.active = False
        row.deactivation_timestamp = datetime.utcnow()
        row.unmute_mod = unmute_mod
        row.unmute_reason = reason
        return row

    @staticmethod
    def upgrade(ban_id: int, mod: int):
        mute = Mute.deactivate(ban_id, mod)
        mute.upgraded = True


class Kick(db.Base):
    __tablename__ = "kick"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    mod: Union[Column, int] = Column(BigInteger)
    timestamp: Union[Column, datetime] = Column(DateTime)
    reason: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))

    @staticmethod
    def create(member: int, member_name: str, mod: int, reason: str) -> "Kick":
        row = Kick(member=member, member_name=member_name, mod=mod, timestamp=datetime.utcnow(), reason=reason)
        db.add(row)
        return row


class Ban(db.Base):
    __tablename__ = "ban"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    mod: Union[Column, int] = Column(BigInteger)
    timestamp: Union[Column, datetime] = Column(DateTime)
    days: Union[Column, int] = Column(Integer)
    reason: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    active: Union[Column, bool] = Column(Boolean)
    deactivation_timestamp: Union[Column, Optional[datetime]] = Column(DateTime, nullable=True)
    unban_reason: Union[Column, Optional[str]] = Column(Text(collation="utf8mb4_bin"), nullable=True)
    unban_mod: Union[Column, Optional[int]] = Column(BigInteger, nullable=True)
    upgraded: Union[Column, bool] = Column(Boolean, default=False)
    is_upgrade: Union[Column, bool] = Column(Boolean)

    @staticmethod
    def create(member: int, member_name: str, mod: int, days: int, reason: str, is_upgrade: bool = False) -> "Ban":
        row = Ban(
            member=member,
            member_name=member_name,
            mod=mod,
            timestamp=datetime.utcnow(),
            days=days,
            reason=reason,
            active=True,
            deactivation_timestamp=None,
            unban_reason=None,
            unban_mod=None,
            is_upgrade=is_upgrade,
        )
        db.add(row)
        return row

    @staticmethod
    def deactivate(ban_id: int, unban_mod: int = None, unban_reason: str = None) -> "Ban":
        row: Ban = db.get(Ban, ban_id)
        row.active = False
        row.deactivation_timestamp = datetime.utcnow()
        row.unban_mod = unban_mod
        row.unban_reason = unban_reason
        return row

    @staticmethod
    def upgrade(ban_id: int, mod: int):
        ban = Ban.deactivate(ban_id, mod)
        ban.upgraded = True
