"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.models.auth import LoginRequest, LoginResponse
from app.services.auth import AuthError, get_idp

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    idp = get_idp()
    try:
        token = await idp.exchange_code(payload.code)
        user = await idp.get_user_info(token)
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, exc.message) from exc
    return LoginResponse(token=token.access_token, user=user)
