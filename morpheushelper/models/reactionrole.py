import re
from typing import Union, Optional

from sqlalchemy import Column, BigInteger, String, Boolean

from PyDrocsid.database import db


def encode(emoji: str) -> str:
    if re.match(r"^<(a?):([a-zA-Z0-9_]+):([0-9]+)>$", emoji):
        return emoji
    return emoji.encode().hex()


def decode(emoji: str) -> str:
    if re.match(r"^<(a?):([a-zA-Z0-9_]+):([0-9]+)>$", emoji):
        return emoji
    return bytes.fromhex(emoji).decode()


class ReactionRole(db.Base):
    __tablename__ = "reactionrole"

    channel_id: Union[Column, int] = Column(BigInteger, primary_key=True)
    message_id: Union[Column, int] = Column(BigInteger, primary_key=True)
    emoji_hex: Union[Column, str] = Column(String(64), primary_key=True)
    role_id: Union[Column, int] = Column(BigInteger)
    auto_remove: Union[Column, bool] = Column(Boolean)

    @staticmethod
    def create(channel_id: int, message_id: int, emoji: str, role_id: int, auto_remove: bool) -> "ReactionRole":
        row = ReactionRole(
            channel_id=channel_id,
            message_id=message_id,
            emoji_hex=encode(emoji),
            role_id=role_id,
            auto_remove=auto_remove,
        )
        db.add(row)
        return row

    @staticmethod
    def get(channel_id: int, message_id: int, emoji: str) -> Optional["ReactionRole"]:
        return db.first(ReactionRole, channel_id=channel_id, message_id=message_id, emoji_hex=encode(emoji))

    @property
    def emoji(self):
        return decode(self.emoji_hex)
