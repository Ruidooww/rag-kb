"""Mock IdP for unit tests."""

from __future__ import annotations

from app.services.auth import IdentityProvider, Token, User


class MockIdP(IdentityProvider):
    """Always returns a pre-configured user."""

    def __init__(self, user: User) -> None:
        self._user = user

    async def exchange_code(self, code: str) -> Token:
        return Token(access_token=f"mock-token-{code}", expires_in=3600)

    async def get_user_info(self, token: Token) -> User:
        return self._user
