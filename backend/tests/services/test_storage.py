from uuid import uuid4

import pytest

from app.core.config import Settings
from app.services import storage as storage_module
from app.services.storage import S3CompatibleStorage, StorageError


def _doc_id() -> str:
    return f"test-{uuid4().hex}.txt"


async def _ready_storage() -> S3CompatibleStorage:
    storage = S3CompatibleStorage()
    await storage.ensure_ready()
    return storage


@pytest.mark.asyncio
@pytest.mark.integration
async def test_save_and_load_roundtrip() -> None:
    storage = await _ready_storage()
    doc_id = _doc_id()
    content = b"hello rustfs"

    uri = await storage.save(doc_id, content, content_type="text/plain")

    assert uri.endswith(f"/documents/{doc_id}")
    assert await storage.load(doc_id) == content


@pytest.mark.asyncio
@pytest.mark.integration
async def test_exists_for_missing_key_returns_false() -> None:
    storage = await _ready_storage()

    assert await storage.exists(_doc_id()) is False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_removes_file() -> None:
    storage = await _ready_storage()
    doc_id = _doc_id()
    await storage.save(doc_id, b"delete me")

    await storage.delete(doc_id)

    assert await storage.exists(doc_id) is False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_presigned_url_returns_http_url() -> None:
    storage = await _ready_storage()
    doc_id = _doc_id()
    await storage.save(doc_id, b"presign me")

    url = await storage.get_presigned_download_url(doc_id, expires_in=600)

    assert url.startswith("http://") or url.startswith("https://")
    assert "X-Amz-Signature=" in url
    assert f"documents/{doc_id}" in url


@pytest.mark.asyncio
async def test_storage_error_on_invalid_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_ENDPOINT", "http://127.0.0.1:1")
    monkeypatch.setattr(storage_module, "settings", Settings())

    storage = S3CompatibleStorage()
    with pytest.raises(StorageError):
        await storage.ensure_ready()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "doc_id",
    ["", "   ", "../secret", "nested/file.txt", r"nested\file.txt"],
)
async def test_invalid_doc_id_rejected(doc_id: str) -> None:
    storage = S3CompatibleStorage()

    with pytest.raises(StorageError):
        await storage.save(doc_id, b"blocked")
