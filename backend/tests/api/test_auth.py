import json
from types import SimpleNamespace

import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.services import auth as auth_module


def _settings(local_users: list[dict[str, object]]) -> SimpleNamespace:
    return SimpleNamespace(
        app_env="dev",
        allow_local_idp_in_prod=False,
        idp_provider="local",
        local_users=json.dumps(local_users),
    )


def _password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def test_login_returns_token_and_user(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_module,
        "settings",
        _settings(
            [
                {
                    "username": "alice",
                    "password_hash": _password_hash("correct-password"),
                    "dept": "tech",
                    "role": "employee",
                }
            ]
        ),
    )

    response = client.post("/api/v1/auth/login", json={"code": "alice:correct-password"})

    assert response.status_code == 200
    body = response.json()
    assert body["token"] == "alice"
    assert body["user"]["user_id"] == "local:alice"
    assert body["user"]["internal_dept_code"] == "tech"
    assert body["user"]["is_external"] is False


def test_login_wrong_password_returns_401(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_module,
        "settings",
        _settings(
            [
                {
                    "username": "alice",
                    "password_hash": _password_hash("correct-password"),
                    "dept": "tech",
                    "role": "employee",
                }
            ]
        ),
    )

    response = client.post("/api/v1/auth/login", json={"code": "alice:wrong-password"})

    assert response.status_code == 401
