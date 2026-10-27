"""Map domain errors to HTTP responses, so services never deal with HTTP status codes."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import (
    AlreadyExistsError,
    AuthenticationError,
    DomainError,
    InvalidOperationError,
    NotFoundError,
    PermissionDeniedError,
)

_STATUS_CODES: dict[type[DomainError], int] = {
    AuthenticationError: 401,
    PermissionDeniedError: 403,
    NotFoundError: 404,
    AlreadyExistsError: 409,
    InvalidOperationError: 409,
}


async def _handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
    status = next((code for cls, code in _STATUS_CODES.items() if isinstance(exc, cls)), 400)
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return JSONResponse(status_code=status, content={"detail": str(exc)}, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
