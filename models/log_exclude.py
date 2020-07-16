from typing import Union, List

from sqlalchemy import Column, BigInteger

from database import db


class LogExclude(db.Base):
    __tablename__ = "log_exclude"

    channel_id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)

    @staticmethod
    def add(channel_id: int):
        db.add(LogExclude(channel_id=channel_id))

    @staticmethod
    def exists(channel_id: int) -> bool:
        return db.get(LogExclude, channel_id) is not None

    @staticmethod
    def all() -> List[int]:
        return [le.channel_id for le in db.query(LogExclude)]

    @staticmethod
    def remove(channel_id: int):
        db.delete(db.get(LogExclude, channel_id))
