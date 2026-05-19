from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.cloud_layout import CloudLayout
from app.index_models import ActiveIndexPointer, ChunkCacheEntry, IndexManifest, build_index_release_name
from app.settings import AppSettings

REQUIRED_STORAGE_FILES = (
    "docstore.json",
    "index_store.json",
    "default__vector_store.json",
)


@dataclass(frozen=True)
class IndexMaterialization:
    storage_dir: Path
    manifest: IndexManifest
    chunk_cache: list[dict]
    source_label: str
    active_pointer: ActiveIndexPointer | None = None


class IndexRepository(Protocol):
    def prepare_runtime_storage(self, default_embed_model: str) -> IndexMaterialization:
        ...

    def has_materialized_index(self) -> bool:
        ...

    def get_build_dir(self) -> Path:
        ...

    def finalize_rebuild(
        self,
        build_dir: Path,
        manifest: IndexManifest,
        chunk_cache: list[dict],
        source: str,
    ) -> ActiveIndexPointer | None:
        ...

    def has_required_storage_files(self) -> bool:
        ...

    def get_runtime_storage_dir(self) -> Path:
        ...


class LocalIndexRepository:
    def __init__(self, settings: AppSettings) -> None:
        self.storage_dir = settings.local_storage_dir
        self.manifest_file = self.storage_dir / "manifest.json"
        self.chunk_cache_file = self.storage_dir / "chunk_cache.json"

    def prepare_runtime_storage(self, default_embed_model: str) -> IndexMaterialization:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        return IndexMaterialization(
            storage_dir=self.storage_dir,
            manifest=self._read_manifest(default_embed_model),
            chunk_cache=self._read_chunk_cache(),
            source_label="local",
        )

    def has_materialized_index(self) -> bool:
        return self.manifest_file.exists() and self.chunk_cache_file.exists()

    def get_build_dir(self) -> Path:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        return self.storage_dir

    def finalize_rebuild(
        self,
        build_dir: Path,
        manifest: IndexManifest,
        chunk_cache: list[dict],
        source: str,
    ) -> ActiveIndexPointer | None:
        build_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file.write_text(
            json.dumps(manifest.to_dict(), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        self.chunk_cache_file.write_text(
            json.dumps(chunk_cache, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        return ActiveIndexPointer.create(
            index_name="local",
            manifest_path="local:manifest.json",
            chunk_cache_path="local:chunk_cache.json",
            storage_prefix="local",
            source=source,
        )

    def has_required_storage_files(self) -> bool:
        return all((self.storage_dir / file_name).exists() for file_name in REQUIRED_STORAGE_FILES)

    def get_runtime_storage_dir(self) -> Path:
        return self.storage_dir

    def _read_manifest(self, default_embed_model: str) -> IndexManifest:
        if not self.manifest_file.exists():
            return IndexManifest.empty(default_embed_model)
        try:
            payload = json.loads(self.manifest_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return IndexManifest.empty(default_embed_model)
        return IndexManifest.from_dict(payload, default_embed_model=default_embed_model)

    def _read_chunk_cache(self) -> list[dict]:
        if not self.chunk_cache_file.exists():
            return []
        try:
            payload = json.loads(self.chunk_cache_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("No fue posible leer el chunk cache local.") from exc
        return [
            item.to_dict()
            for item in (
                ChunkCacheEntry.from_dict(raw_item)
                for raw_item in payload
                if isinstance(raw_item, dict)
            )
            if item.text
        ]


class GCSIndexRepository:
    def __init__(self, settings: AppSettings, cloud_layout: CloudLayout) -> None:
        self.settings = settings
        self.cloud_layout = cloud_layout
        self.cache_root = settings.cloud_index_cache_dir
        self.runtime_dir = self.cache_root / "active"
        self.builds_dir = self.cache_root / "builds"
        self.pointer_cache_file = self.runtime_dir / "active-index.json"

    def prepare_runtime_storage(self, default_embed_model: str) -> IndexMaterialization:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        pointer = self._download_active_pointer()
        if pointer is None:
            return IndexMaterialization(
                storage_dir=self.runtime_dir,
                manifest=IndexManifest.empty(default_embed_model),
                chunk_cache=[],
                source_label="gcs-empty",
                active_pointer=None,
            )

        self._download_runtime_index(pointer)
        manifest = self._read_json_manifest(self.runtime_dir / "manifest.json", default_embed_model)
        chunk_cache = self._read_json_chunk_cache(self.runtime_dir / "chunk_cache.json")
        return IndexMaterialization(
            storage_dir=self.runtime_dir,
            manifest=manifest,
            chunk_cache=chunk_cache,
            source_label="gcs-active",
            active_pointer=pointer,
        )

    def has_materialized_index(self) -> bool:
        return (self.runtime_dir / "manifest.json").exists() and (self.runtime_dir / "chunk_cache.json").exists()

    def get_build_dir(self) -> Path:
        self.builds_dir.mkdir(parents=True, exist_ok=True)
        build_dir = self.builds_dir / build_index_release_name()
        if build_dir.exists():
            shutil.rmtree(build_dir)
        build_dir.mkdir(parents=True, exist_ok=True)
        return build_dir

    def finalize_rebuild(
        self,
        build_dir: Path,
        manifest: IndexManifest,
        chunk_cache: list[dict],
        source: str,
    ) -> ActiveIndexPointer | None:
        manifest_file = build_dir / "manifest.json"
        chunk_cache_file = build_dir / "chunk_cache.json"
        manifest_file.write_text(
            json.dumps(manifest.to_dict(), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        chunk_cache_file.write_text(
            json.dumps(chunk_cache, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

        release_name = build_dir.name
        release_prefix = self.cloud_layout.index_release_prefix(release_name)
        bucket = self._bucket(self.settings.indexes_bucket)

        for path in build_dir.iterdir():
            if path.is_file():
                blob = bucket.blob(f"{release_prefix}/{path.name}")
                blob.upload_from_filename(str(path))

        pointer = ActiveIndexPointer.create(
            index_name=self.settings.active_index_name,
            manifest_path=f"{release_prefix}/manifest.json",
            chunk_cache_path=f"{release_prefix}/chunk_cache.json",
            storage_prefix=release_prefix,
            source=source,
        )
        pointer_blob = bucket.blob(self.cloud_layout.active_index_pointer_blob())
        pointer_blob.upload_from_string(
            json.dumps(pointer.to_dict(), indent=2, ensure_ascii=True),
            content_type="application/json",
        )

        self._replace_runtime_cache_from_build(build_dir, pointer)
        return pointer

    def has_required_storage_files(self) -> bool:
        return all((self.runtime_dir / file_name).exists() for file_name in REQUIRED_STORAGE_FILES)

    def get_runtime_storage_dir(self) -> Path:
        return self.runtime_dir

    def _download_active_pointer(self) -> ActiveIndexPointer | None:
        if not self.settings.indexes_bucket:
            return None

        bucket = self._bucket(self.settings.indexes_bucket)
        blob = bucket.blob(self.cloud_layout.active_index_pointer_blob())
        if not blob.exists():
            return None

        payload = json.loads(blob.download_as_text())
        pointer = ActiveIndexPointer.from_dict(payload)
        self.pointer_cache_file.write_text(
            json.dumps(pointer.to_dict(), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        return pointer

    def _download_runtime_index(self, pointer: ActiveIndexPointer) -> None:
        bucket = self._bucket(self.settings.indexes_bucket)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix="index-sync-", dir=str(self.cache_root)))

        try:
            filenames = {
                "manifest.json": pointer.manifest_path,
                "chunk_cache.json": pointer.chunk_cache_path,
            }
            for required_name in REQUIRED_STORAGE_FILES:
                filenames[required_name] = f"{pointer.storage_prefix}/{required_name}"

            for local_name, remote_path in filenames.items():
                blob = bucket.blob(remote_path)
                if not blob.exists():
                    continue
                blob.download_to_filename(str(temp_dir / local_name))

            self._replace_directory_files(self.runtime_dir, temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _replace_runtime_cache_from_build(self, build_dir: Path, pointer: ActiveIndexPointer) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self._replace_directory_files(self.runtime_dir, build_dir)

        self.pointer_cache_file.write_text(
            json.dumps(pointer.to_dict(), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def _replace_directory_files(self, destination_dir: Path, source_dir: Path) -> None:
        destination_dir.mkdir(parents=True, exist_ok=True)
        temp_destination = Path(tempfile.mkdtemp(prefix="runtime-swap-", dir=str(self.cache_root)))

        try:
            for path in source_dir.iterdir():
                if path.is_file():
                    shutil.copy2(path, temp_destination / path.name)

            for existing in destination_dir.iterdir():
                if existing.is_file():
                    existing.unlink()
                elif existing.is_dir():
                    shutil.rmtree(existing)

            for path in temp_destination.iterdir():
                if path.is_file():
                    shutil.move(str(path), str(destination_dir / path.name))
        finally:
            shutil.rmtree(temp_destination, ignore_errors=True)

    def _read_json_manifest(self, path: Path, default_embed_model: str) -> IndexManifest:
        if not path.exists():
            return IndexManifest.empty(default_embed_model)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("No fue posible leer el manifest del indice materializado.") from exc
        return IndexManifest.from_dict(payload, default_embed_model=default_embed_model)

    def _read_json_chunk_cache(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("No fue posible leer el chunk cache del indice materializado.") from exc
        return [
            item.to_dict()
            for item in (
                ChunkCacheEntry.from_dict(raw_item)
                for raw_item in payload
                if isinstance(raw_item, dict)
            )
            if item.text
        ]

    def _bucket(self, bucket_name: str):
        if not bucket_name:
            raise RuntimeError("Falta configurar INDEXES_BUCKET para usar GCS.")
        from google.cloud import storage

        client = storage.Client(project=self.settings.cloud_project_id or None)
        return client.bucket(bucket_name)


def create_index_repository(settings: AppSettings, cloud_layout: CloudLayout) -> IndexRepository:
    if settings.uses_cloud_indexes:
        return GCSIndexRepository(settings, cloud_layout)
    return LocalIndexRepository(settings)
