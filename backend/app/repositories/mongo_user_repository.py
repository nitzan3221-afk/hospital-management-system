"""MongoDB implementation of ``UserRepository``. Collection ``users``, ``_id`` = username."""

from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from app.domain.errors import AlreadyExistsError
from app.domain.models import User


def _to_document(user: User) -> dict[str, Any]:
    doc = user.model_dump()
    doc["_id"] = doc.pop("username")
    return doc


def _from_document(doc: dict[str, Any]) -> User:
    data = dict(doc)
    data["username"] = data.pop("_id")
    return User.model_validate(data)


class MongoUserRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._collection: AsyncCollection = db["users"]

    async def get_by_username(self, username: str) -> User | None:
        doc = await self._collection.find_one({"_id": username})
        return _from_document(doc) if doc else None

    async def create(self, user: User) -> None:
        try:
            await self._collection.insert_one(_to_document(user))
        except DuplicateKeyError as exc:
            raise AlreadyExistsError(f"User {user.username} already exists") from exc

    async def count(self) -> int:
        return await self._collection.count_documents({})
