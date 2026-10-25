from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    """Liveness + database connectivity check."""
    db_ok = await request.app.state.database.ping()
    return {"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down"}
