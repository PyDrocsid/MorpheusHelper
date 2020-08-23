from typing import Union

from sqlalchemy import Column, Integer, String, BigInteger, Boolean

from PyDrocsid.database import db


class DynamicVoiceChannel(db.Base):
    __tablename__ = "dynamic_voice_channel"

    channel_id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    group_id: Union[Column, int] = Column(Integer)
    text_chat_id: Union[Column, int] = Column(BigInteger)
    owner: Union[Column, int] = Column(BigInteger)

    @staticmethod
    def create(channel_id: int, group_id: int, text_chat_id: int, owner: int) -> "DynamicVoiceChannel":
        row = DynamicVoiceChannel(channel_id=channel_id, group_id=group_id, text_chat_id=text_chat_id, owner=owner)
        db.add(row)
        return row

    @staticmethod
    def change_owner(channel_id: int, owner: int):
        row: DynamicVoiceChannel = db.get(DynamicVoiceChannel, channel_id)
        row.owner = owner


class DynamicVoiceGroup(db.Base):
    __tablename__ = "dynamic_voice_group"

    id: Union[Column, int] = Column(Integer, primary_key=True, unique=True)
    name: Union[Column, str] = Column(String(32))
    channel_id: Union[Column, int] = Column(BigInteger)
    public: Union[Column, bool] = Column(Boolean)

    @staticmethod
    def create(name: str, channel_id: int, public: bool) -> "DynamicVoiceGroup":
        row = DynamicVoiceGroup(name=name, channel_id=channel_id, public=public)
        db.add(row)
        return row
