from fastapi.testclient import TestClient

from app.core.exceptions import ValidationError
from app.main import app


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app_env" in data
    assert "version" in data


def test_app_exception_handler(client: TestClient) -> None:
    async def raise_app_exception() -> None:
        raise ValidationError("test exception", status_code=418)

    app.router.add_api_route("/api/v1/_test/app-exception", raise_app_exception)

    response = client.get("/api/v1/_test/app-exception")
    assert response.status_code == 418
    assert response.json() == {
        "error_code": "VALIDATION_ERROR",
        "message": "test exception",
        "status_code": 418,
    }
