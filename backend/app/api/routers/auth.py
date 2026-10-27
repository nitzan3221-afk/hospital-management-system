from fastapi import APIRouter, Depends

from app.api.dependencies import get_auth_service, get_current_user
from app.api.schemas import LoginRequest, LoginResponse, UserResponse
from app.domain.models import AuthenticatedUser
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, auth: AuthService = Depends(get_auth_service)) -> LoginResponse:
    """Exchange username + password for a JWT access token.

    Seeded users (password ``password123``): ``dr_house`` (doctor), ``nurse_joy`` (nurse),
    ``pam_beesly`` (secretary).
    """
    result = await auth.login(body.username, body.password)
    return LoginResponse(
        access_token=result.access_token,
        expires_at=result.expires_at,
        user=UserResponse.from_user(result.user),
    )


@router.get("/me", response_model=UserResponse)
async def me(user: AuthenticatedUser = Depends(get_current_user)) -> UserResponse:
    """The current user and the permissions their role grants."""
    return UserResponse.from_user(user)
