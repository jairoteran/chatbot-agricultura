from __future__ import annotations

import shutil
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from app.cloud_layout import CloudLayout
from app.index_models import IndexedFileRecord
from app.settings import AppSettings


class DocumentRepository(Protocol):
    def list_pdf_files(self) -> list[IndexedFileRecord]:
        ...

    def prepare_input_dir(self, progress_callback=None) -> Path:
        ...

    def describe_source(self) -> str:
        ...

    def upload_pdf(self, file_name: str, content: bytes) -> IndexedFileRecord:
        ...

    def create_upload_session(
        self,
        file_name: str,
        content_type: str,
        size: int,
        origin: str = "",
    ) -> tuple[str, str]:
        ...

    def get_pdf_record(self, relative_path: str) -> IndexedFileRecord | None:
        ...

    def delete_pdf(self, relative_path: str) -> None:
        ...


class LocalDocumentRepository:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.data_dir = settings.local_data_dir

    def list_pdf_files(self) -> list[IndexedFileRecord]:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        records: list[IndexedFileRecord] = []

        for path in sorted(self.data_dir.rglob("*.pdf")):
            if not path.is_file():
                continue
            stat = path.stat()
            relative_path = str(path.relative_to(self.data_dir)).replace("\\", "/")
            records.append(
                IndexedFileRecord(
                    file_name=path.name,
                    relative_path=relative_path,
                    size=stat.st_size,
                    fingerprint=self._hash_file_contents(path),
                )
            )

        return records

    def prepare_input_dir(self, progress_callback=None) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if progress_callback is not None:
            records = self.list_pdf_files()
            progress_callback(len(records), len(records), "backend/data")
        return self.data_dir

    def describe_source(self) -> str:
        return "backend/data"

    def upload_pdf(self, file_name: str, content: bytes) -> IndexedFileRecord:
        safe_name = Path(file_name).name
        destination = self.data_dir / safe_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        stat = destination.stat()
        return IndexedFileRecord(
            file_name=destination.name,
            relative_path=destination.name,
            size=stat.st_size,
            fingerprint=self._hash_file_contents(destination),
        )

    def create_upload_session(
        self,
        file_name: str,
        content_type: str,
        size: int,
        origin: str = "",
    ) -> tuple[str, str]:
        raise NotImplementedError("Las sesiones de subida directa solo estan disponibles con GCS.")

    def get_pdf_record(self, relative_path: str) -> IndexedFileRecord | None:
        safe_relative = Path(relative_path)
        destination = (self.data_dir / safe_relative).resolve()
        data_root = self.data_dir.resolve()
        if not str(destination).startswith(str(data_root)) or not destination.exists():
            return None

        stat = destination.stat()
        normalized_relative = str(destination.relative_to(self.data_dir)).replace("\\", "/")
        return IndexedFileRecord(
            file_name=destination.name,
            relative_path=normalized_relative,
            size=stat.st_size,
            fingerprint=self._hash_file_contents(destination),
        )

    def delete_pdf(self, relative_path: str) -> None:
        safe_relative = Path(relative_path)
        destination = (self.data_dir / safe_relative).resolve()
        data_root = self.data_dir.resolve()
        if not str(destination).startswith(str(data_root)):
            raise ValueError("La ruta del documento no es valida.")
        if destination.exists():
            destination.unlink()

    def _hash_file_contents(self, path: Path) -> str:
        digest = sha256()
        with path.open("rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


class GcsDocumentRepository:
    def __init__(self, settings: AppSettings, cloud_layout: CloudLayout) -> None:
        if not settings.documents_bucket:
            raise ValueError(
                "DOCUMENTS_BUCKET es obligatorio cuando DOCUMENT_STORAGE_BACKEND=gcs."
            )

        self.settings = settings
        self.cloud_layout = cloud_layout
        self.bucket_name = settings.documents_bucket
        self.prefix = settings.documents_prefix
        self.cache_dir = settings.cloud_documents_cache_dir

    def list_pdf_files(self) -> list[IndexedFileRecord]:
        records: list[IndexedFileRecord] = []
        for blob in self._list_pdf_blobs():
            relative_path = self._relative_path_from_blob(blob.name)
            records.append(
                IndexedFileRecord(
                    file_name=Path(relative_path).name,
                    relative_path=relative_path,
                    size=int(blob.size or 0),
                    fingerprint=self._blob_fingerprint(blob),
                )
            )

        return sorted(records, key=lambda item: item.relative_path)

    def prepare_input_dir(self, progress_callback=None) -> Path:
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        blobs = self._list_pdf_blobs()
        total_blobs = len(blobs)
        for index, blob in enumerate(blobs, start=1):
            relative_path = self._relative_path_from_blob(blob.name)
            destination = self.cache_dir / Path(relative_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(destination))
            if progress_callback is not None:
                progress_callback(index, total_blobs, relative_path)

        return self.cache_dir

    def describe_source(self) -> str:
        return f"gs://{self.bucket_name}/{self.prefix}" if self.prefix else f"gs://{self.bucket_name}"

    def upload_pdf(self, file_name: str, content: bytes) -> IndexedFileRecord:
        safe_name = Path(file_name).name
        blob_path = self.cloud_layout.document_blob_path(safe_name)
        blob = self._client().bucket(self.bucket_name).blob(blob_path)
        blob.upload_from_string(content, content_type="application/pdf")
        blob.reload()
        return IndexedFileRecord(
            file_name=safe_name,
            relative_path=safe_name,
            size=len(content),
            fingerprint=self._blob_fingerprint(blob),
        )

    def create_upload_session(
        self,
        file_name: str,
        content_type: str,
        size: int,
        origin: str = "",
    ) -> tuple[str, str]:
        safe_name = Path(file_name).name
        blob_path = self.cloud_layout.document_blob_path(safe_name)
        blob = self._client().bucket(self.bucket_name).blob(blob_path)
        session_url = blob.create_resumable_upload_session(
            content_type=content_type or "application/pdf",
            size=size,
            origin=origin or None,
        )
        return session_url, safe_name

    def get_pdf_record(self, relative_path: str) -> IndexedFileRecord | None:
        safe_name = Path(relative_path).name
        blob_path = self.cloud_layout.document_blob_path(safe_name)
        blob = self._client().bucket(self.bucket_name).blob(blob_path)
        if not blob.exists():
            return None

        blob.reload()
        return IndexedFileRecord(
            file_name=safe_name,
            relative_path=safe_name,
            size=int(blob.size or 0),
            fingerprint=self._blob_fingerprint(blob),
        )

    def delete_pdf(self, relative_path: str) -> None:
        safe_name = Path(relative_path).name
        blob_path = self.cloud_layout.document_blob_path(safe_name)
        blob = self._client().bucket(self.bucket_name).blob(blob_path)
        if blob.exists():
            blob.delete()

    def _list_pdf_blobs(self):
        bucket = self._client().bucket(self.bucket_name)
        iterator = bucket.list_blobs(prefix=(self.prefix + "/") if self.prefix else None)
        blobs = []
        for blob in iterator:
            if blob.name.endswith("/") or not blob.name.lower().endswith(".pdf"):
                continue
            blobs.append(blob)
        blobs.sort(key=lambda item: item.name)
        return blobs

    def _relative_path_from_blob(self, blob_name: str) -> str:
        if not self.prefix:
            return blob_name.strip("/")
        prefix_with_slash = self.prefix.strip("/") + "/"
        if blob_name.startswith(prefix_with_slash):
            return blob_name[len(prefix_with_slash) :].strip("/")
        return blob_name.strip("/")

    def _blob_fingerprint(self, blob) -> str:
        if getattr(blob, "md5_hash", ""):
            return str(blob.md5_hash)
        if getattr(blob, "crc32c", ""):
            return str(blob.crc32c)
        generation = str(getattr(blob, "generation", "") or "")
        updated = str(getattr(blob, "updated", "") or "")
        return f"{generation}:{updated}"

    def _client(self):
        from google.cloud import storage

        return storage.Client(project=self.settings.cloud_project_id or None)


def create_document_repository(settings: AppSettings, cloud_layout: CloudLayout) -> DocumentRepository:
    if settings.uses_cloud_documents:
        return GcsDocumentRepository(settings, cloud_layout)
    return LocalDocumentRepository(settings)
