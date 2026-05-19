from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class IndexedFileRecord:
    file_name: str
    relative_path: str
    size: int
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "relative_path": self.relative_path,
            "size": self.size,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "IndexedFileRecord":
        return cls(
            file_name=str(payload.get("file_name", "")),
            relative_path=str(payload.get("relative_path", "")),
            size=int(payload.get("size", 0) or 0),
            fingerprint=str(payload.get("fingerprint", "")),
        )


@dataclass(frozen=True)
class IndexManifest:
    manifest_version: int
    embed_model: str
    files: tuple[IndexedFileRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "embed_model": self.embed_model,
            "files": [file.to_dict() for file in self.files],
        }

    @classmethod
    def empty(cls, embed_model: str) -> "IndexManifest":
        return cls(
            manifest_version=2,
            embed_model=embed_model,
            files=(),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any], default_embed_model: str) -> "IndexManifest":
        files = tuple(
            IndexedFileRecord.from_dict(item)
            for item in payload.get("files", [])
            if isinstance(item, dict)
        )
        return cls(
            manifest_version=int(payload.get("manifest_version", 2) or 2),
            embed_model=str(payload.get("embed_model", default_embed_model)),
            files=files,
        )


@dataclass(frozen=True)
class ChunkCacheEntry:
    file_name: str
    page_label: str
    text: str
    tokens: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "page_label": self.page_label,
            "text": self.text,
            "tokens": list(self.tokens),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChunkCacheEntry":
        tokens = tuple(
            str(item)
            for item in payload.get("tokens", [])
            if item is not None
        )
        return cls(
            file_name=str(payload.get("file_name", "")),
            page_label=str(payload.get("page_label", "")),
            text=str(payload.get("text", "")),
            tokens=tokens,
        )


@dataclass(frozen=True)
class ActiveIndexPointer:
    index_name: str
    manifest_path: str
    chunk_cache_path: str
    storage_prefix: str
    updated_at: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_name": self.index_name,
            "manifest_path": self.manifest_path,
            "chunk_cache_path": self.chunk_cache_path,
            "storage_prefix": self.storage_prefix,
            "updated_at": self.updated_at,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActiveIndexPointer":
        return cls(
            index_name=str(payload.get("index_name", "")),
            manifest_path=str(payload.get("manifest_path", "")),
            chunk_cache_path=str(payload.get("chunk_cache_path", "")),
            storage_prefix=str(payload.get("storage_prefix", "")),
            updated_at=str(payload.get("updated_at", "")),
            source=str(payload.get("source", "")),
        )

    @classmethod
    def create(
        cls,
        *,
        index_name: str,
        manifest_path: str,
        chunk_cache_path: str,
        storage_prefix: str,
        source: str,
    ) -> "ActiveIndexPointer":
        return cls(
            index_name=index_name,
            manifest_path=manifest_path,
            chunk_cache_path=chunk_cache_path,
            storage_prefix=storage_prefix,
            updated_at=datetime.now(timezone.utc).isoformat(),
            source=source,
        )


def build_index_release_name() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
