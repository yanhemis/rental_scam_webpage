from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol, Optional

from app.config import get_settings
from app.schemas.extraction_schema import ExtractionResult


class ExtractionCacheBackend(Protocol):
    def get_by_document_id(self, document_id: str) -> Optional[ExtractionResult]:
        ...

    def get_by_content_hash(self, content_hash: str) -> Optional[ExtractionResult]:
        ...

    def set(self, result: ExtractionResult) -> None:
        ...

    def purge_document(self, document_id: str) -> None:
        ...


class InMemoryExtractionCacheBackend:
    def __init__(self) -> None:
        self._by_document_id: dict[str, tuple[ExtractionResult, datetime]] = {}
        self._hash_to_document_id: dict[str, str] = {}

    def _expires_at(self) -> datetime:
        settings = get_settings()
        return datetime.utcnow() + timedelta(seconds=settings.extraction_cache_ttl_seconds)

    def _is_expired(self, expires_at: datetime) -> bool:
        return expires_at <= datetime.utcnow()

    def get_by_document_id(self, document_id: str) -> Optional[ExtractionResult]:
        cached = self._by_document_id.get(document_id)
        if cached is None:
            return None

        result, expires_at = cached
        if self._is_expired(expires_at):
            self.purge_document(document_id)
            return None

        return result.model_copy(update={"cache_hit": True})

    def get_by_content_hash(self, content_hash: str) -> Optional[ExtractionResult]:
        document_id = self._hash_to_document_id.get(content_hash)
        if document_id is None:
            return None
        return self.get_by_document_id(document_id)

    def set(self, result: ExtractionResult) -> None:
        self._by_document_id[result.document_id] = (result, self._expires_at())
        if result.content_hash:
            self._hash_to_document_id[result.content_hash] = result.document_id

    def purge_document(self, document_id: str) -> None:
        cached = self._by_document_id.pop(document_id, None)
        if cached is None:
            return

        result, _expires_at = cached
        if result.content_hash:
            self._hash_to_document_id.pop(result.content_hash, None)


_backend: ExtractionCacheBackend = InMemoryExtractionCacheBackend()


def get_cached_extraction(
    *,
    document_id: str,
    content_hash: Optional[str] = None,
) -> Optional[ExtractionResult]:
    cached = _backend.get_by_document_id(document_id)
    if cached is not None:
        return cached
    if content_hash:
        return _backend.get_by_content_hash(content_hash)
    return None


def cache_extraction(result: ExtractionResult) -> None:
    _backend.set(result)


def purge_document_extraction(document_id: str) -> None:
    _backend.purge_document(document_id)
