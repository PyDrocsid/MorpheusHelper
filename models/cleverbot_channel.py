from typing import Union

from sqlalchemy import Column, BigInteger

from database import db


class CleverBotChannel(db.Base):
    __tablename__ = "cleverbot_channel"

    channel: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)

    @staticmethod
    def create(channel: int) -> "CleverBotChannel":
        row = CleverBotChannel(channel=channel)
        db.add(row)
        return row
