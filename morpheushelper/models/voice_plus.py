from datetime import datetime
from typing import Union
from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, Integer
from PyDrocsid.database import db


class VoicePlusMember(db.Base):
    __tablename__ = "voicemember"

    id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    name: Union[Column, str] = Column(String(128))

    @staticmethod
    def create(id: int, name: str) -> "VoicePlusMember":
        row = VoicePlusMember(id=guild_id, name=code)
        db.add(row)
        return row


class VoiceMutedLog(db.Base):
    __tablename__ = "voicemutedlog"
    id: Union[Column, int] = Column(
        Integer, primary_key=True, unique=True, autoincrement=True)
    member: Union[Column, int] = Column(BigInteger)
    member_name: Union[Column, str] = Column(Text(collation="utf8mb4_bin"))
    timestamp: Union[Column, datetime] = Column(DateTime)

    @staticmethod
    def create(member: int, member_name: str, timestamp: Optional[datetime] = None) -> "VoiceMutedLog":
        row = VoiceMutedLog(member=member, member_name=member_name,
                            timestamp=timestamp or datetime.utcnow())
        db.add(row)
        return row
