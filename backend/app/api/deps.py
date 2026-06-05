"""FastAPI dependency providers."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from app.services.storage import DocumentStorage, StorageError

__all__ = ["get_storage"]


def get_storage(request: Request) -> DocumentStorage:
    """Return the document storage bound to the FastAPI app state."""
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise StorageError("Document storage is not initialized")
    return cast(DocumentStorage, storage)
