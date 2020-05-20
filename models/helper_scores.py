from typing import Union

from sqlalchemy import Column, BigInteger, Integer

from database import db


class HelperScores(db.Base):
    __tablename__ = "helper_scores"

    user_id: Union[Column, int] = Column(BigInteger, primary_key=True, unique=True)
    score: Union[Column, int] = Column(Integer)

    @staticmethod
    def create(user_id: int, score: int) -> "HelperScores":
        scores: HelperScores = HelperScores(user_id=user_id, score=score)
        
        db.add(scores)

        return scores

    @staticmethod
    def get(user_id: int) -> "HelperScores":
        if (row := db.get(HelperScores, user_id)) is None:
            return HelperScores.create(user_id, 0)

        return row

    @staticmethod
    def set(user_id: int, score: int) -> "HelperScores":
        if (row := db.get(HelperScores, user_id)) is None:
            return HelperScores.create(user_id, score)

        row.score = score
        return row