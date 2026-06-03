from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from app.cloud_layout import CloudLayout
from app.index_models import ActiveIndexPointer, IndexManifest
from app.metadata_models import (
    DOCUMENT_STATUS_INDEXED,
    DocumentRecord,
    ReindexJobRecord,
    RuntimeStateRecord,
    utc_now_iso,
)
from app.settings import AppSettings


class MetadataRepository(Protocol):
    def sync_documents(
        self,
        manifest: IndexManifest,
        documents_prefix: str,
        corpus_analysis: dict[str, dict] | None = None,
    ) -> None:
        ...

    def upsert_document_record(self, record: DocumentRecord) -> None:
        ...

    def delete_document_record(self, relative_path: str) -> None:
        ...

    def list_document_records(self) -> list[DocumentRecord]:
        ...

    def start_reindex_job(self, trigger: str, source: str, *, total_documents: int = 0) -> str:
        ...

    def update_reindex_progress(
        self,
        job_id: str,
        *,
        progress: int,
        stage: str,
        detail: str,
        total_documents: int = 0,
        processed_documents: int = 0,
    ) -> None:
        ...

    def finish_reindex_job(
        self,
        job_id: str,
        *,
        status: str,
        release_name: str = "",
        error_message: str = "",
    ) -> None:
        ...

    def update_active_index(
        self,
        *,
        pointer: ActiveIndexPointer | None,
        manifest: IndexManifest,
        source: str,
        job_id: str = "",
        status: str = "success",
    ) -> None:
        ...

    def get_runtime_state(self) -> RuntimeStateRecord:
        ...

    def reconcile_runtime_success(self) -> None:
        ...


class NoopMetadataRepository:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.runtime_state = RuntimeStateRecord()

    def sync_documents(
        self,
        manifest: IndexManifest,
        documents_prefix: str,
        corpus_analysis: dict[str, dict] | None = None,
    ) -> None:
        return None

    def upsert_document_record(self, record: DocumentRecord) -> None:
        return None

    def delete_document_record(self, relative_path: str) -> None:
        return None

    def list_document_records(self) -> list[DocumentRecord]:
        return []

    def start_reindex_job(self, trigger: str, source: str, *, total_documents: int = 0) -> str:
        return f"noop-{uuid4().hex[:12]}"

    def update_reindex_progress(
        self,
        job_id: str,
        *,
        progress: int,
        stage: str,
        detail: str,
        total_documents: int = 0,
        processed_documents: int = 0,
    ) -> None:
        now = utc_now_iso()
        self.runtime_state = RuntimeStateRecord(
            active_index_name=self.runtime_state.active_index_name,
            active_index_source=self.runtime_state.active_index_source,
            active_index_manifest_path=self.runtime_state.active_index_manifest_path,
            last_successful_reindex=self.runtime_state.last_successful_reindex,
            last_failed_reindex=self.runtime_state.last_failed_reindex,
            last_reindex_status="running",
            last_reindex_job_id=job_id,
            reindex_progress=max(0, min(progress, 100)),
            reindex_stage=stage,
            reindex_detail=detail,
            reindex_total_documents=max(0, total_documents),
            reindex_processed_documents=max(0, processed_documents),
            updated_at=now,
        )

    def finish_reindex_job(
        self,
        job_id: str,
        *,
        status: str,
        release_name: str = "",
        error_message: str = "",
    ) -> None:
        now = utc_now_iso()
        self.runtime_state = RuntimeStateRecord(
            active_index_name=self.runtime_state.active_index_name,
            active_index_source=self.runtime_state.active_index_source,
            active_index_manifest_path=self.runtime_state.active_index_manifest_path,
            last_successful_reindex=now if status == "success" else self.runtime_state.last_successful_reindex,
            last_failed_reindex=now if status != "success" else self.runtime_state.last_failed_reindex,
            last_reindex_status=status,
            last_reindex_job_id=job_id,
            reindex_progress=100 if status == "success" else self.runtime_state.reindex_progress,
            reindex_stage="completed" if status == "success" else "failed",
            reindex_detail=(
                "Reindexado completado correctamente."
                if status == "success"
                else (error_message or "El reindexado manual fallo.")
            ),
            reindex_total_documents=self.runtime_state.reindex_total_documents,
            reindex_processed_documents=(
                self.runtime_state.reindex_total_documents
                if status == "success"
                else self.runtime_state.reindex_processed_documents
            ),
            updated_at=now,
        )

    def update_active_index(
        self,
        *,
        pointer: ActiveIndexPointer | None,
        manifest: IndexManifest,
        source: str,
        job_id: str = "",
        status: str = "success",
    ) -> None:
        now = utc_now_iso()
        manifest_path = pointer.manifest_path if pointer is not None else "local:manifest.json"
        active_name = pointer.index_name if pointer is not None else self.settings.active_index_name
        self.runtime_state = RuntimeStateRecord(
            active_index_name=active_name,
            active_index_source=source,
            active_index_manifest_path=manifest_path,
            last_successful_reindex=now if status == "success" else self.runtime_state.last_successful_reindex,
            last_failed_reindex=self.runtime_state.last_failed_reindex,
            last_reindex_status=status,
            last_reindex_job_id=job_id or self.runtime_state.last_reindex_job_id,
            reindex_progress=100 if status == "success" else self.runtime_state.reindex_progress,
            reindex_stage="completed" if status == "success" else self.runtime_state.reindex_stage,
            reindex_detail=(
                "Reindexado completado correctamente."
                if status == "success"
                else self.runtime_state.reindex_detail
            ),
            reindex_total_documents=self.runtime_state.reindex_total_documents,
            reindex_processed_documents=(
                self.runtime_state.reindex_total_documents
                if status == "success"
                else self.runtime_state.reindex_processed_documents
            ),
            updated_at=now,
        )

    def get_runtime_state(self) -> RuntimeStateRecord:
        return self.runtime_state

    def reconcile_runtime_success(self) -> None:
        now = utc_now_iso()
        preserved_job_id = (
            self.runtime_state.last_reindex_job_id
            if self.runtime_state.last_reindex_status == "success"
            else ""
        )
        self.runtime_state = RuntimeStateRecord(
            active_index_name=self.runtime_state.active_index_name,
            active_index_source=self.runtime_state.active_index_source,
            active_index_manifest_path=self.runtime_state.active_index_manifest_path,
            last_successful_reindex=self.runtime_state.last_successful_reindex or now,
            last_failed_reindex=self.runtime_state.last_failed_reindex,
            last_reindex_status="success",
            last_reindex_job_id=preserved_job_id,
            reindex_progress=100,
            reindex_stage="completed",
            reindex_detail="Reindexado completado correctamente.",
            reindex_total_documents=self.runtime_state.reindex_total_documents,
            reindex_processed_documents=self.runtime_state.reindex_total_documents,
            updated_at=now,
        )


class FirestoreMetadataRepository:
    def __init__(self, settings: AppSettings, cloud_layout: CloudLayout) -> None:
        self.settings = settings
        self.cloud_layout = cloud_layout

    def sync_documents(
        self,
        manifest: IndexManifest,
        documents_prefix: str,
        corpus_analysis: dict[str, dict] | None = None,
    ) -> None:
        documents = self._documents_collection()
        analysis_by_path = corpus_analysis or {}
        for item in manifest.files:
            storage_path = self.cloud_layout.document_blob_path(item.relative_path)
            analysis = analysis_by_path.get(item.relative_path, {})
            record = DocumentRecord(
                document_id=item.fingerprint[:24] or item.relative_path.replace("/", "_"),
                file_name=item.file_name,
                relative_path=item.relative_path,
                storage_path=storage_path if self.settings.uses_cloud_documents else f"local:{item.relative_path}",
                fingerprint=item.fingerprint,
                size=item.size,
                status=DOCUMENT_STATUS_INDEXED,
                topics=analysis.get("topics", []),
                entities=analysis.get("entities", []),
                key_terms=analysis.get("key_terms", []),
                nlp_analyzer=analysis.get("nlp_analyzer", ""),
            )
            documents.document(record.document_id).set(record.to_dict(), merge=True)

    def upsert_document_record(self, record: DocumentRecord) -> None:
        self._documents_collection().document(record.document_id).set(record.to_dict(), merge=True)

    def delete_document_record(self, relative_path: str) -> None:
        documents = self._documents_collection()
        for snapshot in documents.where("relative_path", "==", relative_path).stream():
            snapshot.reference.delete()

    def list_document_records(self) -> list[DocumentRecord]:
        records: list[DocumentRecord] = []
        for snapshot in self._documents_collection().stream():
            payload = snapshot.to_dict() or {}
            records.append(DocumentRecord.from_dict(payload))
        return sorted(records, key=lambda item: item.relative_path)

    def start_reindex_job(self, trigger: str, source: str, *, total_documents: int = 0) -> str:
        job_id = f"job-{uuid4().hex[:16]}"
        record = ReindexJobRecord(
            job_id=job_id,
            trigger=trigger,
            status="running",
            source=source,
            progress=0,
            stage="queued",
            detail="Reindexado en cola para ejecucion.",
            total_documents=max(0, total_documents),
            processed_documents=0,
        )
        self._jobs_collection().document(job_id).set(record.to_dict(), merge=True)
        self._runtime_document().set(
            RuntimeStateRecord(
                **{
                    **self.get_runtime_state().to_dict(),
                    "last_reindex_status": "running",
                    "last_reindex_job_id": job_id,
                    "reindex_progress": 0,
                    "reindex_stage": "queued",
                    "reindex_detail": "Reindexado en cola para ejecucion.",
                    "reindex_total_documents": max(0, total_documents),
                    "reindex_processed_documents": 0,
                    "updated_at": utc_now_iso(),
                }
            ).to_dict(),
            merge=True,
        )
        return job_id

    def update_reindex_progress(
        self,
        job_id: str,
        *,
        progress: int,
        stage: str,
        detail: str,
        total_documents: int = 0,
        processed_documents: int = 0,
    ) -> None:
        clamped_progress = max(0, min(progress, 100))
        now = utc_now_iso()
        self._jobs_collection().document(job_id).set(
            {
                "status": "running",
                "progress": clamped_progress,
                "stage": stage,
                "detail": detail,
                "total_documents": max(0, total_documents),
                "processed_documents": max(0, processed_documents),
                "updated_at": now,
            },
            merge=True,
        )
        current = self.get_runtime_state()
        self._runtime_document().set(
            RuntimeStateRecord(
                active_index_name=current.active_index_name,
                active_index_source=current.active_index_source,
                active_index_manifest_path=current.active_index_manifest_path,
                last_successful_reindex=current.last_successful_reindex,
                last_failed_reindex=current.last_failed_reindex,
                last_reindex_status="running",
                last_reindex_job_id=job_id,
                reindex_progress=clamped_progress,
                reindex_stage=stage,
                reindex_detail=detail,
                reindex_total_documents=max(0, total_documents),
                reindex_processed_documents=max(0, processed_documents),
                updated_at=now,
            ).to_dict(),
            merge=True,
        )

    def finish_reindex_job(
        self,
        job_id: str,
        *,
        status: str,
        release_name: str = "",
        error_message: str = "",
    ) -> None:
        now = utc_now_iso()
        current = self.get_runtime_state()
        self._jobs_collection().document(job_id).set(
            {
                "status": status,
                "progress": 100 if status == "success" else current.reindex_progress,
                "stage": "completed" if status == "success" else "failed",
                "detail": (
                    "Reindexado completado correctamente."
                    if status == "success"
                    else (error_message or "El reindexado manual fallo.")
                ),
                "total_documents": current.reindex_total_documents,
                "processed_documents": current.reindex_processed_documents,
                "finished_at": now,
                "release_name": release_name,
                "error_message": error_message,
                "updated_at": now,
            },
            merge=True,
        )
        self._runtime_document().set(
            RuntimeStateRecord(
                active_index_name=current.active_index_name,
                active_index_source=current.active_index_source,
                active_index_manifest_path=current.active_index_manifest_path,
                last_successful_reindex=now if status == "success" else current.last_successful_reindex,
                last_failed_reindex=now if status != "success" else current.last_failed_reindex,
                last_reindex_status=status,
                last_reindex_job_id=job_id,
                reindex_progress=100 if status == "success" else current.reindex_progress,
                reindex_stage="completed" if status == "success" else "failed",
                reindex_detail=(
                    "Reindexado completado correctamente."
                    if status == "success"
                    else (error_message or "El reindexado manual fallo.")
                ),
                reindex_total_documents=current.reindex_total_documents,
                reindex_processed_documents=current.reindex_processed_documents,
                updated_at=now,
            ).to_dict(),
            merge=True,
        )

    def update_active_index(
        self,
        *,
        pointer: ActiveIndexPointer | None,
        manifest: IndexManifest,
        source: str,
        job_id: str = "",
        status: str = "success",
    ) -> None:
        now = utc_now_iso()
        active_name = pointer.index_name if pointer is not None else self.settings.active_index_name
        manifest_path = pointer.manifest_path if pointer is not None else "local:manifest.json"
        self._runtime_document().set(
            RuntimeStateRecord(
                active_index_name=active_name,
                active_index_source=source,
                active_index_manifest_path=manifest_path,
                last_successful_reindex=now if status == "success" else self.get_runtime_state().last_successful_reindex,
                last_failed_reindex=self.get_runtime_state().last_failed_reindex,
                last_reindex_status=status,
                last_reindex_job_id=job_id,
                reindex_progress=100 if status == "success" else self.get_runtime_state().reindex_progress,
                reindex_stage="completed" if status == "success" else self.get_runtime_state().reindex_stage,
                reindex_detail=(
                    "Reindexado completado correctamente."
                    if status == "success"
                    else self.get_runtime_state().reindex_detail
                ),
                reindex_total_documents=self.get_runtime_state().reindex_total_documents,
                reindex_processed_documents=self.get_runtime_state().reindex_processed_documents,
                updated_at=now,
            ).to_dict(),
            merge=True,
        )

    def get_runtime_state(self) -> RuntimeStateRecord:
        snapshot = self._runtime_document().get()
        if not snapshot.exists:
            return RuntimeStateRecord()
        payload = snapshot.to_dict() or {}
        return RuntimeStateRecord.from_dict(payload)

    def reconcile_runtime_success(self) -> None:
        current = self.get_runtime_state()
        if not current.active_index_name:
            return

        now = utc_now_iso()
        preserved_job_id = (
            current.last_reindex_job_id
            if current.last_reindex_status == "success"
            else ""
        )
        self._runtime_document().set(
            RuntimeStateRecord(
                active_index_name=current.active_index_name,
                active_index_source=current.active_index_source,
                active_index_manifest_path=current.active_index_manifest_path,
                last_successful_reindex=current.last_successful_reindex or now,
                last_failed_reindex=current.last_failed_reindex,
                last_reindex_status="success",
                last_reindex_job_id=preserved_job_id,
                reindex_progress=100,
                reindex_stage="completed",
                reindex_detail="Reindexado completado correctamente.",
                reindex_total_documents=current.reindex_total_documents,
                reindex_processed_documents=current.reindex_total_documents,
                updated_at=now,
            ).to_dict(),
            merge=True,
        )

    def _documents_collection(self):
        return self._client().collection(self.settings.firestore_documents_collection)

    def _jobs_collection(self):
        return self._client().collection(self.settings.firestore_jobs_collection)

    def _runtime_document(self):
        return self._client().collection(self.settings.firestore_runtime_collection).document("active")

    def _client(self):
        from google.cloud import firestore

        return firestore.Client(project=self.settings.cloud_project_id or None)


def create_metadata_repository(settings: AppSettings, cloud_layout: CloudLayout) -> MetadataRepository:
    if settings.metadata_backend == "firestore" or settings.process_state_backend == "firestore":
        return FirestoreMetadataRepository(settings, cloud_layout)
    return NoopMetadataRepository(settings)
