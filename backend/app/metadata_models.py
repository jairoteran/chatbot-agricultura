from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

DOCUMENT_STATUS_PENDING_INDEX = "pending_index"
DOCUMENT_STATUS_INDEXED = "indexed"
DOCUMENT_STATUS_DELETED = "deleted"
DOCUMENT_STATUS_FAILED = "failed"
DOCUMENT_STATUSES = {
    DOCUMENT_STATUS_PENDING_INDEX,
    DOCUMENT_STATUS_INDEXED,
    DOCUMENT_STATUS_DELETED,
    DOCUMENT_STATUS_FAILED,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_document_status(status: str) -> str:
    cleaned = str(status or "").strip().lower()
    return cleaned if cleaned in DOCUMENT_STATUSES else DOCUMENT_STATUS_PENDING_INDEX


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    file_name: str
    relative_path: str
    storage_path: str
    fingerprint: str
    size: int
    status: str = DOCUMENT_STATUS_INDEXED
    topics: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    key_terms: list[str] = field(default_factory=list)
    nlp_analyzer: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "file_name": self.file_name,
            "relative_path": self.relative_path,
            "storage_path": self.storage_path,
            "fingerprint": self.fingerprint,
            "size": self.size,
            "status": normalize_document_status(self.status),
            "topics": self.topics,
            "entities": self.entities,
            "key_terms": self.key_terms,
            "nlp_analyzer": self.nlp_analyzer,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DocumentRecord":
        return cls(
            document_id=str(payload.get("document_id", "")),
            file_name=str(payload.get("file_name", "")),
            relative_path=str(payload.get("relative_path", "")),
            storage_path=str(payload.get("storage_path", "")),
            fingerprint=str(payload.get("fingerprint", "")),
            size=int(payload.get("size", 0) or 0),
            status=normalize_document_status(str(payload.get("status", ""))),
            topics=_string_list(payload.get("topics", [])),
            entities=_string_list(payload.get("entities", [])),
            key_terms=_string_list(payload.get("key_terms", [])),
            nlp_analyzer=str(payload.get("nlp_analyzer", "")),
            created_at=str(payload.get("created_at", "")) or utc_now_iso(),
            updated_at=str(payload.get("updated_at", "")) or utc_now_iso(),
        )


@dataclass(frozen=True)
class ReindexJobRecord:
    job_id: str
    trigger: str
    status: str
    source: str
    progress: int = 0
    stage: str = ""
    detail: str = ""
    total_documents: int = 0
    processed_documents: int = 0
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str = ""
    release_name: str = ""
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "trigger": self.trigger,
            "status": self.status,
            "source": self.source,
            "progress": self.progress,
            "stage": self.stage,
            "detail": self.detail,
            "total_documents": self.total_documents,
            "processed_documents": self.processed_documents,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "release_name": self.release_name,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class RuntimeStateRecord:
    active_index_name: str = ""
    active_index_source: str = ""
    active_index_manifest_path: str = ""
    last_successful_reindex: str = ""
    last_failed_reindex: str = ""
    last_reindex_status: str = ""
    last_reindex_job_id: str = ""
    reindex_progress: int = 0
    reindex_stage: str = ""
    reindex_detail: str = ""
    reindex_total_documents: int = 0
    reindex_processed_documents: int = 0
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_index_name": self.active_index_name,
            "active_index_source": self.active_index_source,
            "active_index_manifest_path": self.active_index_manifest_path,
            "last_successful_reindex": self.last_successful_reindex,
            "last_failed_reindex": self.last_failed_reindex,
            "last_reindex_status": self.last_reindex_status,
            "last_reindex_job_id": self.last_reindex_job_id,
            "reindex_progress": self.reindex_progress,
            "reindex_stage": self.reindex_stage,
            "reindex_detail": self.reindex_detail,
            "reindex_total_documents": self.reindex_total_documents,
            "reindex_processed_documents": self.reindex_processed_documents,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeStateRecord":
        return cls(
            active_index_name=str(payload.get("active_index_name", "")),
            active_index_source=str(payload.get("active_index_source", "")),
            active_index_manifest_path=str(payload.get("active_index_manifest_path", "")),
            last_successful_reindex=str(payload.get("last_successful_reindex", "")),
            last_failed_reindex=str(payload.get("last_failed_reindex", "")),
            last_reindex_status=str(payload.get("last_reindex_status", "")),
            last_reindex_job_id=str(payload.get("last_reindex_job_id", "")),
            reindex_progress=int(payload.get("reindex_progress", 0) or 0),
            reindex_stage=str(payload.get("reindex_stage", "")),
            reindex_detail=str(payload.get("reindex_detail", "")),
            reindex_total_documents=int(payload.get("reindex_total_documents", 0) or 0),
            reindex_processed_documents=int(payload.get("reindex_processed_documents", 0) or 0),
            updated_at=str(payload.get("updated_at", "")) or utc_now_iso(),
        )
