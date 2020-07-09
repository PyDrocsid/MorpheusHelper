from datetime import datetime, timedelta
from typing import Union

from sqlalchemy import Column, String, BigInteger, DateTime

from database import db


class RedditChannel(db.Base):
    __tablename__ = "reddit_channel"

    subreddit: Union[Column, str] = Column(String(32), primary_key=True)
    channel: Union[Column, int] = Column(BigInteger, primary_key=True)

    @staticmethod
    def create(subreddit: str, channel: int) -> "RedditChannel":
        row = RedditChannel(subreddit=subreddit, channel=channel)
        db.add(row)
        return row


class RedditPost(db.Base):
    __tablename__ = "reddit_post"

    post_id: Union[Column, str] = Column(String(16), primary_key=True, unique=True)
    timestamp: Union[Column, datetime] = Column(DateTime)

    @staticmethod
    def create(post_id: str) -> "RedditPost":
        row = RedditPost(post_id=post_id, timestamp=datetime.utcnow())
        db.add(row)
        return row

    @staticmethod
    def clean():
        drop_before_timestamp = datetime.utcnow() - timedelta(weeks=1)
        db.query(RedditPost).filter(RedditPost.timestamp < drop_before_timestamp).delete()

    @staticmethod
    def post(post_id: str) -> bool:
        if db.get(RedditPost, post_id) is not None:
            return False
        RedditPost.create(post_id)
        return True
