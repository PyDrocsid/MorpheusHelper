from typing import Union
from sqlalchemy import Column, String, BigInteger, DateTime, Integer

from PyDrocsid.database import db


class Links(db.Base):
    __tablename__ = "links"

    link_id: Union[Column, int] = Column(Integer, primary_key=True)
    link: Union[Column, str] = Column(String)

    @staticmethod
    def create(link_id: int, link: str) -> "Links":
        row = Links(link_id=link_id, link=link)
        db.add(row)
        return row

