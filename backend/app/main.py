"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.middleware import REQUEST_ID_HEADER, request_context_middleware
from app.api.routers import auth, health, patients
from app.core.config import get_settings
from app.core.database import MongoDatabase
from app.core.logging_config import configure_logging
from app.repositories.mongo_patient_repository import MongoPatientRepository
from app.repositories.mongo_user_repository import MongoUserRepository
from app.seed import seed_database

logger = logging.getLogger("hospital.app")


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

    logger.info("Application started", extra={"db": settings.mongo_db})
    yield
    await database.close()
    logger.info("Application stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

    app.middleware("http")(request_context_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )

    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(patients.router)

    return app


app = create_app()
