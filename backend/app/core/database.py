"""MongoDB connection management."""

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError


class MongoDatabase:
    """Owns the lifecycle of the MongoDB client and exposes the application database."""

    def __init__(self, uri: str, db_name: str) -> None:
        # tz_aware=True -> datetimes come back as timezone-aware UTC values
        self._client: AsyncMongoClient = AsyncMongoClient(uri, tz_aware=True)
        self.db: AsyncDatabase = self._client[db_name]

    async def ping(self) -> bool:
        """Return True if the database answers a ping."""
        try:
            await self.db.command("ping")
            return True
        except PyMongoError:
            return False

    async def close(self) -> None:
        await self._client.close()
