from typing import Union, Optional, Type, TypeVar

from sqlalchemy import Column, String

from database import db

T = TypeVar("T")


class Settings(db.Base):
    __tablename__ = "settings"

    key: Union[Column, str] = Column(String(64), primary_key=True, unique=True)
    value: Union[Column, str] = Column(String(256))

    @staticmethod
    def create(key: str, value: Union[str, int, float, bool]) -> "Settings":
        if isinstance(value, bool):
            value = int(value)

        row = Settings(key=key, value=str(value))
        db.add(row)
        return row

    @staticmethod
    def get(dtype: Type[T], key: str, default: Optional[T] = None) -> Optional[T]:
        if (row := db.get(Settings, key)) is None:
            if default is None:
                return None
            row = Settings.create(key, default)

        out: str = row.value
        if dtype == bool:
            out: int = int(out)
        return dtype(out)

    @staticmethod
    def set(dtype: Type[T], key: str, value: T) -> "Settings":
        if (row := db.get(Settings, key)) is None:
            return Settings.create(key, value)

        if dtype == bool:
            value = int(value)
        row.value = str(value)
        return row
