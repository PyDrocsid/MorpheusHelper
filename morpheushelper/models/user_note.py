from datetime import datetime
from typing import Union

from PyDrocsid.database import db
from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, Integer


class UserNote(db.Base):
    __tablename__ = "user_note"

    id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    member: Union[Column, int] = Column(BigInteger)
    description: Union[Column, str] = Column(String(2000))
    timestamp: Union[Column, datetime] = Column(DateTime)

    @staticmethod
    def create(member: int, description: str) -> "UserNote":
        row = UserNote(
            member=member,
            description=description,
            timestamp=datetime.utcnow()
        )
        db.add(row)
        return row
