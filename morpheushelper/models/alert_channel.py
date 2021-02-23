from typing import Union

from PyDrocsid.database import db
from sqlalchemy import Column, BigInteger


class AlertChannel(db.Base):
    __tablename__ = "alert_channel"

    guild: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    channel: Union[Column, int] = Column(BigInteger)

    @staticmethod
    def create(guild: int, channel: int) -> "AlertChannel":
        row = AlertChannel(guild=guild, channel=channel)
        db.add(row)
        return row
