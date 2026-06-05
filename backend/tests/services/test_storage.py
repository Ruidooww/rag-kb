from uuid import uuid4

import pytest

from app.services.storage import S3CompatibleStorage, StorageError, get_storage

pytestmark = pytest.mark.integration


def _doc_id() -> str:
    return f"test-{uuid4().hex}.txt"


@pytest.mark.asyncio
async def test_save_and_load_roundtrip() -> None:
    storage = get_storage()
    doc_id = _doc_id()
    content = b"hello rustfs"

    uri = await storage.save(doc_id, content, content_type="text/plain")

    assert uri.endswith(f"/documents/{doc_id}")
    assert await storage.load(doc_id) == content


@pytest.mark.asyncio
async def test_exists_for_missing_key_returns_false() -> None:
    storage = get_storage()

    assert await storage.exists(_doc_id()) is False


@pytest.mark.asyncio
async def test_delete_removes_file() -> None:
    storage = get_storage()
    doc_id = _doc_id()
    await storage.save(doc_id, b"delete me")

    await storage.delete(doc_id)

    assert await storage.exists(doc_id) is False


@pytest.mark.asyncio
async def test_get_presigned_url_returns_http_url() -> None:
    storage = get_storage()
    doc_id = _doc_id()
    await storage.save(doc_id, b"presign me")

    url = await storage.get_presigned_download_url(doc_id, expires_in=600)

    assert url.startswith("http://") or url.startswith("https://")
    assert "X-Amz-Signature=" in url
    assert f"documents/{doc_id}" in url


def test_storage_error_on_invalid_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.storage.settings.storage_endpoint", "http://127.0.0.1:1")

    with pytest.raises(StorageError):
        S3CompatibleStorage()
