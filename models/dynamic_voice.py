from typing import Union

from sqlalchemy import Column, Integer, String, BigInteger

from database import db


class DynamicVoiceChannel(db.Base):
    __tablename__ = "dynamic_voice_channel"

    channel_id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    group_id: Union[Column, int] = Column(Integer)

    @staticmethod
    def create(channel_id: int, group_id: int) -> "DynamicVoiceChannel":
        row = DynamicVoiceChannel(channel_id=channel_id, group_id=group_id)
        db.add(row)
        return row


class DynamicVoiceGroup(db.Base):
    __tablename__ = "dynamic_voice_group"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True)
    name: Union[Column, str] = Column(String(32))
    channel_id: Union[Column, int] = Column(BigInteger)

    @staticmethod
    def create(name: str, channel_id: int) -> "DynamicVoiceGroup":
        row = DynamicVoiceGroup(name=name, channel_id=channel_id)
        db.add(row)
        return row
