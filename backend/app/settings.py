from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _detect_deployment_target() -> str:
    explicit_target = os.getenv("APP_DEPLOYMENT_TARGET", "").strip().lower()
    if explicit_target:
        return explicit_target

    if os.getenv("K_SERVICE"):
        return "cloud-run"
    if os.getenv("VERCEL") == "1":
        return "vercel"
    if os.getenv("RENDER") == "true":
        return "render"
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return "railway"
    if os.getenv("FLY_APP_NAME"):
        return "fly"
    return "local"


def _env_flag(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name, "").strip().lower()
    if not raw_value:
        return default
    return raw_value in {"1", "true", "yes", "on"}


def _env_csv(name: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return ()
    return tuple(
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    )


@dataclass(frozen=True)
class AppSettings:
    root_dir: Path
    backend_dir: Path
    local_data_dir: Path
    local_storage_dir: Path
    cloud_index_cache_dir: Path
    cloud_documents_cache_dir: Path
    deployment_target: str
    document_storage_backend: str
    index_storage_backend: str
    metadata_backend: str
    process_state_backend: str
    cloud_project_id: str
    cloud_region: str
    documents_bucket: str
    documents_prefix: str
    indexes_bucket: str
    indexes_prefix: str
    active_index_name: str
    firestore_documents_collection: str
    firestore_jobs_collection: str
    firestore_runtime_collection: str
    gemini_model: str
    openai_model: str
    allow_runtime_reindex: bool
    google_auth_client_id: str
    admin_emails: tuple[str, ...]
    admin_session_secret: str
    admin_session_ttl_seconds: int
    admin_base_path: str
    reindex_job_name: str

    @property
    def uses_local_documents(self) -> bool:
        return self.document_storage_backend == "local"

    @property
    def uses_local_index_storage(self) -> bool:
        return self.index_storage_backend == "local"

    @property
    def uses_cloud_documents(self) -> bool:
        return self.document_storage_backend == "gcs"

    @property
    def uses_cloud_indexes(self) -> bool:
        return self.index_storage_backend == "gcs"

    @property
    def admin_auth_enabled(self) -> bool:
        return bool(
            self.google_auth_client_id
            and self.admin_session_secret
            and self.admin_emails
        )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    backend_dir = BACKEND_DIR
    root_dir = backend_dir.parent
    deployment_target = _detect_deployment_target()
    allow_runtime_reindex = _env_flag(
        "ALLOW_RUNTIME_REINDEX",
        default=deployment_target == "local",
    )

    return AppSettings(
        root_dir=root_dir,
        backend_dir=backend_dir,
        local_data_dir=Path(os.getenv("LOCAL_DATA_DIR", backend_dir / "data")),
        local_storage_dir=Path(os.getenv("LOCAL_STORAGE_DIR", backend_dir / "storage")),
        cloud_index_cache_dir=Path(os.getenv("CLOUD_INDEX_CACHE_DIR", backend_dir / "storage" / "_cloud_index_cache")),
        cloud_documents_cache_dir=Path(
            os.getenv("CLOUD_DOCUMENTS_CACHE_DIR", backend_dir / "storage" / "_cloud_documents_cache")
        ),
        deployment_target=deployment_target,
        document_storage_backend=os.getenv("DOCUMENT_STORAGE_BACKEND", "local").strip().lower() or "local",
        index_storage_backend=os.getenv("INDEX_STORAGE_BACKEND", "local").strip().lower() or "local",
        metadata_backend=os.getenv("METADATA_BACKEND", "none").strip().lower() or "none",
        process_state_backend=os.getenv("PROCESS_STATE_BACKEND", "none").strip().lower() or "none",
        cloud_project_id=os.getenv("GOOGLE_CLOUD_PROJECT", "").strip(),
        cloud_region=os.getenv("GOOGLE_CLOUD_REGION", "us-central1").strip() or "us-central1",
        documents_bucket=os.getenv("DOCUMENTS_BUCKET", "").strip(),
        documents_prefix=os.getenv("DOCUMENTS_PREFIX", "documents").strip().strip("/"),
        indexes_bucket=os.getenv("INDEXES_BUCKET", "").strip(),
        indexes_prefix=os.getenv("INDEXES_PREFIX", "indexes").strip().strip("/"),
        active_index_name=os.getenv("ACTIVE_INDEX_NAME", "current").strip() or "current",
        firestore_documents_collection=os.getenv("FIRESTORE_DOCUMENTS_COLLECTION", "documents").strip() or "documents",
        firestore_jobs_collection=os.getenv("FIRESTORE_JOBS_COLLECTION", "reindex_jobs").strip() or "reindex_jobs",
        firestore_runtime_collection=os.getenv("FIRESTORE_RUNTIME_COLLECTION", "runtime_state").strip() or "runtime_state",
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash",
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini").strip() or "gpt-5.4-mini",
        allow_runtime_reindex=allow_runtime_reindex,
        google_auth_client_id=os.getenv("GOOGLE_AUTH_CLIENT_ID", "").strip(),
        admin_emails=_env_csv("ADMIN_EMAILS"),
        admin_session_secret=os.getenv("ADMIN_SESSION_SECRET", "").strip(),
        admin_session_ttl_seconds=max(300, int(os.getenv("ADMIN_SESSION_TTL_SECONDS", "28800").strip() or "28800")),
        admin_base_path=os.getenv("ADMIN_BASE_PATH", "/gestion").strip() or "/gestion",
        reindex_job_name=os.getenv("REINDEX_JOB_NAME", "tesis-producto-reindex").strip() or "tesis-producto-reindex",
    )
