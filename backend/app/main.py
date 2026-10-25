"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import MongoDatabase
from app.repositories.mongo_patient_repository import MongoPatientRepository
from app.repositories.mongo_user_repository import MongoUserRepository
from app.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the database connection on startup and close it on shutdown."""
    settings = get_settings()
    database = MongoDatabase(settings.mongo_uri, settings.mongo_db)
    app.state.database = database

    patient_repo = MongoPatientRepository(database.db)
    await patient_repo.ensure_indexes()
    if settings.seed_on_startup:
        await seed_database(patient_repo, MongoUserRepository(database.db))

    yield
    await database.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["health"])
    async def health(request: Request) -> dict[str, str]:
        """Liveness + database connectivity check."""
        db_ok = await request.app.state.database.ping()
        return {"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down"}

    return app


app = create_app()
