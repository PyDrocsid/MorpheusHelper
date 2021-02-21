from typing import Union, Optional, Type, TypeVar

from sqlalchemy import Column, String

from PyDrocsid.database import db, db_thread

T = TypeVar("T")


class Settings(db.Base):
    __tablename__ = "settings"

    key: Union[Column, str] = Column(String(64), primary_key=True, unique=True)
    value: Union[Column, str] = Column(String(256))

    @staticmethod
    def _create(key: str, value: Union[str, int, float, bool]) -> "Settings":
        if isinstance(value, bool):
            value = int(value)

        row = Settings(key=key, value=str(value))
        db.add(row)
        return row

    @staticmethod
    def _get(dtype: Type[T], key: str, default: Optional[T] = None) -> Optional[T]:
        if (row := db.get(Settings, key)) is None:
            if default is None:
                return None
            row = Settings._create(key, default)

        out: str = row.value
        if dtype == bool:
            out: int = int(out)
        return dtype(out)

    @staticmethod
    def _set(dtype: Type[T], key: str, value: T) -> "Settings":
        if (row := db.get(Settings, key)) is None:
            return Settings._create(key, value)

        if dtype == bool:
            value = int(value)
        row.value = str(value)
        return row

    @staticmethod
    async def get(dtype: Type[T], key: str, default: Optional[T] = None) -> Optional[T]:
        return await db_thread(Settings._get, dtype, key, default)

    @staticmethod
    async def set(dtype: Type[T], key: str, value: T):
        await db_thread(Settings._set, dtype, key, value)
