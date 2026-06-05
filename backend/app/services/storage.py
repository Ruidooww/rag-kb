"""Document object storage abstraction layer."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Final, cast

import boto3
from anyio import to_thread
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Request
from loguru import logger

from app.core.config import settings
from app.core.exceptions import AppException

__all__ = ["DocumentStorage", "S3CompatibleStorage", "StorageError", "get_storage"]

_BUCKET_KEY_PREFIX: Final = "documents"
_DOC_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9._-]+$")
_NO_SUCH_BUCKET_CODES: Final = {"404", "NoSuchBucket", "NotFound"}
_NO_SUCH_KEY_CODES: Final = {"404", "NoSuchKey", "NotFound"}


class StorageError(AppException):
    error_code = "STORAGE_ERROR"
    status_code = 502


class DocumentStorage(ABC):
    @abstractmethod
    async def save(
        self,
        doc_id: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Save document content and return a storage URI."""

    @abstractmethod
    async def load(self, doc_id: str) -> bytes:
        """Load document bytes by document id."""

    @abstractmethod
    async def delete(self, doc_id: str) -> None:
        """Delete document content if it exists."""

    @abstractmethod
    async def exists(self, doc_id: str) -> bool:
        """Return whether document content exists."""

    @abstractmethod
    async def get_presigned_download_url(self, doc_id: str, *, expires_in: int = 3600) -> str:
        """Return a temporary download URL."""


class S3CompatibleStorage(DocumentStorage):
    """S3-compatible storage implementation for RustFS and similar backends."""

    def __init__(self) -> None:
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint,
            aws_access_key_id=settings.storage_access_key.get_secret_value(),
            aws_secret_access_key=settings.storage_secret_key.get_secret_value(),
            region_name=settings.storage_region,
            config=Config(signature_version="s3v4"),
        )
        self._bucket = settings.storage_bucket

    async def ensure_ready(self) -> None:
        """Ensure the backing bucket exists and is reachable."""
        await to_thread.run_sync(self._ensure_bucket)

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            if _client_error_code(exc) not in _NO_SUCH_BUCKET_CODES:
                raise StorageError(f"Failed to access bucket {self._bucket}") from exc
            self._client.create_bucket(Bucket=self._bucket)
            logger.info("Created bucket {}", self._bucket)
        except BotoCoreError as exc:
            raise StorageError(f"Failed to access bucket {self._bucket}") from exc

    def _key(self, doc_id: str) -> str:
        normalized_doc_id = doc_id.strip()
        if not normalized_doc_id:
            raise StorageError("Document id must not be empty")
        if not _DOC_ID_PATTERN.fullmatch(normalized_doc_id):
            raise StorageError(f"Invalid document id: {doc_id}")
        return f"{_BUCKET_KEY_PREFIX}/{normalized_doc_id}"

    async def save(
        self,
        doc_id: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        key = self._key(doc_id)
        try:
            await to_thread.run_sync(
                lambda: self._client.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=content,
                    ContentType=content_type,
                )
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Failed to save {doc_id}") from exc
        return f"s3://{self._bucket}/{key}"

    async def load(self, doc_id: str) -> bytes:
        key = self._key(doc_id)
        try:
            response = cast(
                dict[str, Any],
                await to_thread.run_sync(
                    lambda: self._client.get_object(Bucket=self._bucket, Key=key)
                ),
            )
            body = response["Body"]
            return cast(bytes, await to_thread.run_sync(body.read))
        except ClientError as exc:
            if _client_error_code(exc) in _NO_SUCH_KEY_CODES:
                raise StorageError(f"Document not found: {doc_id}") from exc
            raise StorageError(f"Failed to load {doc_id}") from exc
        except BotoCoreError as exc:
            raise StorageError(f"Failed to load {doc_id}") from exc

    async def delete(self, doc_id: str) -> None:
        key = self._key(doc_id)
        try:
            await to_thread.run_sync(
                lambda: self._client.delete_object(Bucket=self._bucket, Key=key)
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Failed to delete {doc_id}") from exc

    async def exists(self, doc_id: str) -> bool:
        key = self._key(doc_id)
        try:
            await to_thread.run_sync(lambda: self._client.head_object(Bucket=self._bucket, Key=key))
            return True
        except ClientError as exc:
            if _client_error_code(exc) in _NO_SUCH_KEY_CODES:
                return False
            raise StorageError(f"Failed to check {doc_id}") from exc
        except BotoCoreError as exc:
            raise StorageError(f"Failed to check {doc_id}") from exc

    async def get_presigned_download_url(self, doc_id: str, *, expires_in: int = 3600) -> str:
        key = self._key(doc_id)
        try:
            return cast(
                str,
                await to_thread.run_sync(
                    lambda: self._client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": self._bucket, "Key": key},
                        ExpiresIn=expires_in,
                    )
                ),
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Failed to presign URL for {doc_id}") from exc


def get_storage(request: Request) -> DocumentStorage:
    """Return the configured document storage implementation."""
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise StorageError("Document storage is not initialized")
    return cast(DocumentStorage, storage)


def _client_error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))
