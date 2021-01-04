from typing import Union

from PyDrocsid.database import db
from sqlalchemy import Column, BigInteger


class ReactionPinChannel(db.Base):
    __tablename__ = "reactionpin_channel"

    channel: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)

    @staticmethod
    def create(channel: int) -> "ReactionPinChannel":
        row = ReactionPinChannel(channel=channel)
        db.add(row)
        return row
