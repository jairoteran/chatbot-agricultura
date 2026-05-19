from __future__ import annotations

from dataclasses import dataclass

from app.settings import AppSettings


def _join_parts(*parts: str) -> str:
    cleaned = [part.strip("/") for part in parts if part and part.strip("/")]
    return "/".join(cleaned)


@dataclass(frozen=True)
class CloudLayout:
    documents_prefix: str
    indexes_prefix: str
    active_index_name: str

    def document_blob_path(self, relative_path: str) -> str:
        return _join_parts(self.documents_prefix, relative_path)

    def index_release_prefix(self, release_name: str) -> str:
        return _join_parts(self.indexes_prefix, "releases", release_name)

    def active_index_prefix(self) -> str:
        return _join_parts(self.indexes_prefix, self.active_index_name)

    def active_index_pointer_blob(self) -> str:
        return _join_parts(self.indexes_prefix, "active-index.json")

    def release_manifest_blob(self, release_name: str) -> str:
        return _join_parts(self.index_release_prefix(release_name), "manifest.json")

    def release_chunk_cache_blob(self, release_name: str) -> str:
        return _join_parts(self.index_release_prefix(release_name), "chunk_cache.json")


def get_cloud_layout(settings: AppSettings) -> CloudLayout:
    return CloudLayout(
        documents_prefix=settings.documents_prefix,
        indexes_prefix=settings.indexes_prefix,
        active_index_name=settings.active_index_name,
    )
