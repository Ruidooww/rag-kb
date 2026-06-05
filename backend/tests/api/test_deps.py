from types import SimpleNamespace

import pytest
from starlette.requests import Request

from app.api.deps import get_storage
from app.services.storage import S3CompatibleStorage, StorageError


def test_get_storage_returns_app_state_storage() -> None:
    storage = S3CompatibleStorage()
    request = Request(
        {"type": "http", "app": SimpleNamespace(state=SimpleNamespace(storage=storage))}
    )

    assert get_storage(request) is storage


def test_get_storage_requires_initialized_state() -> None:
    request = Request({"type": "http", "app": SimpleNamespace(state=SimpleNamespace())})

    with pytest.raises(StorageError):
        get_storage(request)
