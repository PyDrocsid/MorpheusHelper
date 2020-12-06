from typing import Union

from PyDrocsid.database import db
from sqlalchemy import Column, BigInteger, Text


class AOCLink(db.Base):
    __tablename__ = "aoc_link"

    discord_id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    aoc_id: Union[Column, str] = Column(Text, unique=True)

    @staticmethod
    def create(discord_id: int, aoc_id: str) -> "AOCLink":
        link = AOCLink(discord_id=discord_id, aoc_id=aoc_id)
        db.add(link)
        return link
