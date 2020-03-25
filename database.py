import asyncio
from os import environ as env

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session


class DB:
    def __init__(self, hostname, port, database, username, password):
        self.engine: Engine = create_engine(
            f"mysql+pymysql://{username}:{password}@{hostname}:{port}/{database}", pool_pre_ping=True
        )

        self._SessionFactory: sessionmaker = sessionmaker(bind=self.engine)
        self._Session = scoped_session(self._SessionFactory)
        self.Base: DeclarativeMeta = declarative_base()

    def create_tables(self):
        self.Base.metadata.create_all(bind=db.engine)

    def close(self):
        self._Session.remove()

    def add(self, obj):
        self.session.add(obj)

    def delete(self, obj):
        self.session.delete(obj)

    def query(self, model, **kwargs):
        return self.session.query(model).filter_by(**kwargs)

    def first(self, model, **kwargs):
        return self.query(model, **kwargs).first()

    def get(self, model, primary_key):
        return self.session.query(model).get(primary_key)

    @property
    def session(self):
        return self._Session()


async def run_in_thread(function, *args, **kwargs):
    def inner():
        out = function(*args, **kwargs)
        db.session.commit()
        db.close()
        return out

    result = await asyncio.get_running_loop().run_in_executor(None, inner)
    return result


db: DB = DB(
    hostname=env.get("DB_HOST", "localhost"),
    port=env.get("DB_PORT", 3306),
    database=env.get("DB_DATABASE", "morpheushelper"),
    username=env.get("DB_USER", "morpheushelper"),
    password=env.get("DB_PASSWORD", "morpheushelper"),
)
