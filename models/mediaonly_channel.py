from typing import Union

from sqlalchemy import Column, BigInteger

from database import db


class MediaOnlyChannel(db.Base):
    __tablename__ = "mediaonly_channel"

    channel: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)

    @staticmethod
    def create(channel: int) -> "MediaOnlyChannel":
        row = MediaOnlyChannel(channel=channel)
        db.add(row)
        return row
