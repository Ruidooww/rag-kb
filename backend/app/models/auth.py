from pydantic import BaseModel

from app.services.auth import User


class LoginRequest(BaseModel):
    code: str


class LoginResponse(BaseModel):
    token: str
    user: User
