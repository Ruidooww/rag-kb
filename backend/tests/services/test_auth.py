import json
from types import SimpleNamespace

import bcrypt
import pytest

from app.models.document_meta import Visibility
from app.services import auth as auth_module
from app.services.auth import (
    AuthError,
    FeishuIdP,
    IdentityProvider,
    LocalIdP,
    Token,
    User,
    WeChatMpIdP,
    WeChatOpenIdP,
    WeComIdP,
    get_idp,
)


def _password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _settings(
    *,
    local_users: list[dict[str, object]] | None = None,
    app_env: str = "dev",
    allow_local_idp_in_prod: bool = False,
    idp_provider: str = "local",
) -> SimpleNamespace:
    return SimpleNamespace(
        app_env=app_env,
        allow_local_idp_in_prod=allow_local_idp_in_prod,
        idp_provider=idp_provider,
        local_users=json.dumps(local_users or []),
    )


def test_user_schema_defaults_are_internal() -> None:
    user = User(
        user_id="local:alice",
        external_provider="local",
        external_user_id="alice",
        display_name="Alice",
    )

    assert user.allowed_depts == []
    assert user.is_external is False
    assert user.max_visibility == Visibility.INTERNAL


@pytest.mark.asyncio
async def test_local_idp_login_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_module,
        "settings",
        _settings(
            local_users=[
                {
                    "username": "alice",
                    "password_hash": _password_hash("correct-password"),
                    "dept": "tech",
                    "role": "manager",
                    "display_name": "Alice Zhang",
                    "email": "alice@example.com",
                    "is_external": True,
                }
            ]
        ),
    )
    idp = LocalIdP()

    token = await idp.exchange_code("alice:correct-password")
    user = await idp.get_user_info(token)

    assert token.access_token == "alice"
    assert token.expires_in == 86400
    assert user.user_id == "local:alice"
    assert user.internal_dept_code == "tech"
    assert user.allowed_depts == ["tech"]
    assert user.max_visibility == Visibility.CONFIDENTIAL
    assert user.is_external is False
    assert user.display_name == "Alice Zhang"
    assert user.email == "alice@example.com"


@pytest.mark.asyncio
async def test_local_idp_login_wrong_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_module,
        "settings",
        _settings(
            local_users=[
                {
                    "username": "alice",
                    "password_hash": _password_hash("correct-password"),
                    "dept": "tech",
                    "role": "employee",
                }
            ]
        ),
    )
    idp = LocalIdP()

    with pytest.raises(AuthError, match="Wrong password"):
        await idp.exchange_code("alice:wrong-password")


@pytest.mark.asyncio
async def test_local_idp_unknown_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_module, "settings", _settings())
    idp = LocalIdP()

    with pytest.raises(AuthError, match="Unknown user"):
        await idp.exchange_code("missing:anything")


def test_local_idp_rejects_production_without_escape_hatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_module,
        "settings",
        _settings(app_env="production", allow_local_idp_in_prod=False),
    )

    with pytest.raises(AuthError, match="disabled in production"):
        LocalIdP()


def test_local_idp_allows_production_with_escape_hatch_and_warns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warnings: list[str] = []
    monkeypatch.setattr(
        auth_module,
        "settings",
        _settings(app_env="production", allow_local_idp_in_prod=True),
    )
    monkeypatch.setattr(auth_module.logger, "warning", lambda message: warnings.append(message))

    LocalIdP()

    assert warnings == ["LocalIdP enabled in PRODUCTION via ALLOW_LOCAL_IDP_IN_PROD escape hatch"]


def test_get_idp_returns_local_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_module, "settings", _settings(idp_provider="local"))

    assert isinstance(get_idp(), LocalIdP)


@pytest.mark.parametrize(
    ("provider", "expected_type"),
    [
        ("feishu", FeishuIdP),
        ("wecom", WeComIdP),
        ("wechat_open", WeChatOpenIdP),
        ("wechat_mp", WeChatMpIdP),
    ],
)
def test_get_idp_returns_stub_provider(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    expected_type: type[IdentityProvider],
) -> None:
    monkeypatch.setattr(auth_module, "settings", _settings(idp_provider=provider))

    assert isinstance(get_idp(), expected_type)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_cls", [FeishuIdP, WeComIdP, WeChatOpenIdP, WeChatMpIdP])
async def test_stub_providers_raise_not_implemented(
    provider_cls: type[IdentityProvider],
) -> None:
    idp = provider_cls()

    with pytest.raises(NotImplementedError):
        await idp.exchange_code("code")
    with pytest.raises(NotImplementedError):
        await idp.get_user_info(Token(access_token="token"))
