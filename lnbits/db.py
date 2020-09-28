import os
import aiosqlite
from typing import Dict

from .settings import LNBITS_DATA_FOLDER


class Database:
    def __init__(self, db_path: str):
        self.path = db_path

    async def connect(self):
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row
        self.cursor = await self.connection.cursor()
        return self

    async def __aenter__(self):
        self.cursor = await self.connection.cursor()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            await self.connection.rollback()
        else:
            await self.connection.commit()

    async def commit(self):
        await self.connection.commit()

    async def rollback(self):
        await self.connection.rollback()

    async def fetchall(self, query: str, values: tuple = ()) -> list:
        await self.execute(query, values)
        return await self.cursor.fetchall()

    async def fetchone(self, query: str, values: tuple = ()):
        await self.execute(query, values)
        return await self.cursor.fetchone()

    async def execute(self, query: str, values: tuple = ()) -> None:
        try:
            await self.cursor.execute(query, values)
        except aiosqlite.Error as exc:
            print("sqlite error", exc)
            await self.rollback()
            raise exc


_db_objects: Dict[str, Database] = {}


async def open_db(db_name: str = "database") -> Database:
    try:
        return _db_objects[db_name]
    except KeyError:
        db_path = os.path.join(LNBITS_DATA_FOLDER, f"{db_name}.sqlite3")
        _db_objects[db_name] = await Database(db_path).connect()
        return _db_objects[db_name]


async def open_ext_db(extension_name: str) -> Database:
    return await open_db(f"ext_{extension_name}")
