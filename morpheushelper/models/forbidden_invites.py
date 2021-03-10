from datetime import datetime
from typing import Union

from PyDrocsid.database import db
from sqlalchemy import Column, BigInteger, DateTime, String


class ForbiddenInvites(db.Base):
    __tablename__ = "forbidden_invite"

    id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    code: Union[Column, str] = Column(String(16))
    timestamp: Union[Column, datetime] = Column(DateTime)
    member: Union[Column, int] = Column(BigInteger)

    @staticmethod
    def create(code: str, member: int) -> "ForbiddenInvites":
        row = ForbiddenInvites(
            code=code,
            member=member,
            timestamp=datetime.utcnow(),
        )
        db.add(row)
        return row
