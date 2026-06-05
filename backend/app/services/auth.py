"""Identity Provider abstraction layer."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Final

import bcrypt
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.document_meta import Visibility

__all__ = [
    "AuthError",
    "FeishuIdP",
    "IdentityProvider",
    "LocalIdP",
    "Token",
    "User",
    "WeChatMpIdP",
    "WeChatOpenIdP",
    "WeComIdP",
    "get_idp",
]

_ROLE_MAX_VISIBILITY: Final[dict[str, Visibility]] = {
    "employee": Visibility.INTERNAL,
    "manager": Visibility.CONFIDENTIAL,
    "admin": Visibility.CONFIDENTIAL,
}


class AuthError(AppException):
    error_code = "AUTH_ERROR"
    status_code = 401


class Token(BaseModel):
    access_token: str
    expires_in: int = 3600


class User(BaseModel):
    """Logged-in user context for ACL and agent tool selection."""

    user_id: str
    external_provider: str
    external_user_id: str
    display_name: str
    email: str | None = None
    internal_dept_code: str | None = None
    role: str = "employee"
    max_visibility: Visibility = Visibility.INTERNAL
    allowed_depts: list[str] = Field(default_factory=list)
    is_external: bool = False


class IdentityProvider(ABC):
    """Interface implemented by all identity providers."""

    @abstractmethod
    async def exchange_code(self, code: str) -> Token:
        """Exchange an auth code or local credential string for a token."""

    @abstractmethod
    async def get_user_info(self, token: Token) -> User:
        """Return normalized user information for a token."""


class LocalIdP(IdentityProvider):
    """Local username/password IdP for development and tests."""

    def __init__(self) -> None:
        if settings.app_env == "production" and not settings.allow_local_idp_in_prod:
            raise AuthError(
                "LocalIdP is disabled in production. "
                "Set ALLOW_LOCAL_IDP_IN_PROD=true to override (emergency only)."
            )
        if settings.app_env == "production" and settings.allow_local_idp_in_prod:
            logger.warning(
                "LocalIdP enabled in PRODUCTION via ALLOW_LOCAL_IDP_IN_PROD escape hatch"
            )

        try:
            self._users = _parse_local_users(settings.local_users)
        except (json.JSONDecodeError, TypeError) as exc:
            raise AuthError(f"Invalid LOCAL_USERS config: {exc}") from exc

    async def exchange_code(self, code: str) -> Token:
        try:
            username, password = code.split(":", 1)
        except ValueError as exc:
            raise AuthError("Code must be 'username:password' for LocalIdP") from exc

        user = self._users.get(username)
        if user is None:
            raise AuthError(f"Unknown user: {username}")

        if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            raise AuthError("Wrong password")

        return Token(access_token=username, expires_in=86400)

    async def get_user_info(self, token: Token) -> User:
        username = token.access_token
        user = self._users.get(username)
        if user is None:
            raise AuthError(f"Token references unknown user: {username}")

        role = user.get("role", "employee")
        dept = user.get("dept")
        return User(
            user_id=f"local:{username}",
            external_provider="local",
            external_user_id=username,
            display_name=user.get("display_name", username),
            email=user.get("email"),
            internal_dept_code=dept,
            role=role,
            max_visibility=_ROLE_MAX_VISIBILITY.get(role, Visibility.INTERNAL),
            allowed_depts=[dept] if dept else [],
            is_external=False,
        )


class FeishuIdP(IdentityProvider):
    """Feishu OAuth stub. Implement in #42 prep task."""

    async def exchange_code(self, code: str) -> Token:
        raise NotImplementedError("FeishuIdP: implement in #42 prep task")

    async def get_user_info(self, token: Token) -> User:
        raise NotImplementedError("FeishuIdP: implement in #42 prep task")


class WeComIdP(IdentityProvider):
    """WeCom OAuth stub. Implement in #42 prep task."""

    async def exchange_code(self, code: str) -> Token:
        raise NotImplementedError("WeComIdP: implement in #42 prep task")

    async def get_user_info(self, token: Token) -> User:
        raise NotImplementedError("WeComIdP: implement in #42 prep task")


class WeChatOpenIdP(IdentityProvider):
    """WeChat Open Platform login stub for external users.

    Future implementations must return ``User.is_external=True`` and
    ``Visibility.PUBLIC`` because these users are outside the company.
    """

    async def exchange_code(self, code: str) -> Token:
        raise NotImplementedError("WeChatOpenIdP: implement when external login needed")

    async def get_user_info(self, token: Token) -> User:
        raise NotImplementedError("WeChatOpenIdP: implement when external login needed")


class WeChatMpIdP(IdentityProvider):
    """WeChat official account stub for external customer-service access.

    Future implementations must return ``User.is_external=True`` and
    ``Visibility.PUBLIC``; this provider should only feed public routes.
    """

    async def exchange_code(self, code: str) -> Token:
        raise NotImplementedError("WeChatMpIdP: implement for external customer service")

    async def get_user_info(self, token: Token) -> User:
        raise NotImplementedError("WeChatMpIdP: implement for external customer service")


_PROVIDERS: Final[dict[str, type[IdentityProvider]]] = {
    "local": LocalIdP,
    "feishu": FeishuIdP,
    "wecom": WeComIdP,
    "wechat_open": WeChatOpenIdP,
    "wechat_mp": WeChatMpIdP,
}


def _parse_local_users(raw: str) -> dict[str, dict[str, str]]:
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise TypeError("LOCAL_USERS must be a JSON list")

    users: dict[str, dict[str, str]] = {}
    for item in parsed:
        if not isinstance(item, dict):
            raise TypeError("LOCAL_USERS entries must be JSON objects")
        username = item.get("username")
        password_hash = item.get("password_hash")
        if not isinstance(username, str) or not isinstance(password_hash, str):
            raise TypeError("LOCAL_USERS entries require username and password_hash")
        users[username] = _string_values(item)
    return users


def _string_values(item: dict[Any, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in item.items() if value is not None}


def get_idp() -> IdentityProvider:
    provider_cls = _PROVIDERS.get(settings.idp_provider)
    if provider_cls is None:
        raise AuthError(f"Unknown IDP_PROVIDER: {settings.idp_provider}")
    return provider_cls()
