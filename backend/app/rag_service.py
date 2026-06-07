from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import Any

from app.settings import get_settings
from app.cloud_layout import get_cloud_layout
from app.corpus_analyzer import analyze_corpus_document
from app.document_repository import create_document_repository
from app.index_models import ChunkCacheEntry, IndexManifest
from app.index_repository import create_index_repository
from app.metadata_repository import create_metadata_repository

settings = get_settings()
cloud_layout = get_cloud_layout(settings)
index_repository = create_index_repository(settings, cloud_layout)
metadata_repository = create_metadata_repository(settings, cloud_layout)
document_repository = create_document_repository(settings, cloud_layout)
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OPENAI_MODEL = settings.openai_model
GEMINI_MODEL = settings.gemini_model
GEMINI_FALLBACK_MODEL = settings.gemini_fallback_model
LLM_TIMEOUT_SECONDS = settings.llm_timeout_seconds
TOP_K = 4
SIMILARITY_THRESHOLD = 0.42
MAX_RESPONSE_EVIDENCE = 3
MAX_RESPONSE_SOURCE_EXCERPT = 420
MAX_LLM_EVIDENCE_CHARS = 900
STOP_WORDS = {
    "a",
    "al",
    "ante",
    "bajo",
    "cabe",
    "con",
    "contra",
    "cual",
    "cuales",
    "como",
    "cuando",
    "de",
    "del",
    "desde",
    "donde",
    "el",
    "ella",
    "ellas",
    "ellos",
    "en",
    "entre",
    "era",
    "eramos",
    "es",
    "esa",
    "esas",
    "ese",
    "eso",
    "esos",
    "esta",
    "estas",
    "este",
    "esto",
    "estos",
    "fue",
    "ha",
    "hacia",
    "hasta",
    "hay",
    "la",
    "las",
    "le",
    "les",
    "lo",
    "los",
    "mas",
    "mi",
    "mis",
    "o",
    "para",
    "pero",
    "por",
    "que",
    "quien",
    "quienes",
    "se",
    "segun",
    "si",
    "sin",
    "sobre",
    "su",
    "sus",
    "te",
    "tu",
    "tus",
    "un",
    "una",
    "uno",
    "unas",
    "unos",
    "y",
    "ya",
}
GENERIC_TOPIC_WORDS = {
    "agricultura",
    "agricultores",
    "ancestrales",
    "cargados",
    "cultivo",
    "cultivos",
    "documento",
    "documentos",
    "ecuador",
    "informacion",
    "manejo",
    "pdf",
    "pdfs",
    "practicas",
    "pregunta",
    "produccion",
    "saberes",
    "sector",
    "sistema",
    "sistemas",
    "texto",
    "textos",
}
SMALL_TALK_PATTERNS = [
    (
        re.compile(r"^(hola|buenas|buenos dias|buen dia|buenas tardes|buenas noches)[!. ]*$", re.IGNORECASE),
        "Hola. Estoy listo para ayudarte con tus documentos. Puedes preguntarme por cultivos, practicas, recomendaciones o pedir un resumen claro de lo que dicen los textos.",
    ),
    (
        re.compile(r"^(como estas|como te encuentras|que tal|como vas)[?!. ]*$", re.IGNORECASE),
        "Estoy bien y listo para ayudarte. Si quieres, puedes hacerme una pregunta sobre los documentos o pedirme que te explique un tema de forma mas clara y ordenada.",
    ),
    (
        re.compile(r"^(gracias|muchas gracias)[!. ]*$", re.IGNORECASE),
        "Con gusto. Si quieres, seguimos con otra pregunta o con un resumen mas claro sobre algun tema de los documentos.",
    ),
    (
        re.compile(r"^(quien eres|que eres|que puedes hacer)[?!. ]*$", re.IGNORECASE),
        "Soy un asistente documental. Puedo revisar la informacion de tus PDFs, resumirla, explicarla de forma clara y ayudarte a encontrar ideas importantes sin copiar el texto tal cual.",
    ),
]
DOCUMENT_COUNT_PATTERNS = [
    re.compile(r"^\s*cu[aá]ntos?\s+documentos?\s+(tienes|hay|tengo|dispones|tienen)\s*[?!. ]*$", re.IGNORECASE),
    re.compile(r"^\s*cu[aá]l\s+es\s+el\s+total\s+de\s+documentos?\s*[?!. ]*$", re.IGNORECASE),
    re.compile(r"^\s*cu[aá]ntos?\s+pdfs?\s+(tienes|hay|dispones|tienen)\s*[?!. ]*$", re.IGNORECASE),
]
RESPONSE_STYLE_GUIDANCE = {
    "academico": {
        "label": "Academico",
        "sections": ("**Respuesta breve:**", "**Puntos clave:**", "**Conclusion:**", "**Nota:**"),
        "related_label": "**Temas relacionados:**",
        "fallback_points_label": "**Puntos rescatables:**",
        "summary_instruction": (
            "Redacta como si fuera un apoyo para tesis o informe academico, con tono formal y relaciones claras entre ideas."
        ),
        "llm_instruction": (
            "Usa un tono academico claro y ordenado, pero responde de forma directa y segura. "
            "No repitas frases como 'segun el documento' o 'los documentos indican' dentro de cada idea. "
            "Deja que el respaldo documental viva en las fuentes del panel, no en el cuerpo de la respuesta. "
            "Desarrolla la respuesta con contexto, relaciones entre ideas y una explicacion un poco mas amplia que una contestacion breve."
        ),
        "length_instruction": (
            "Apunta a 3 o 4 parrafos breves bien desarrollados. Explica la idea principal, desarrolla sus matices "
            "y cierra con una interpretacion util o implicacion relevante."
        ),
    },
    "simple": {
        "label": "Simple",
        "sections": ("**Explicacion breve:**", "**Ideas principales:**", "**En resumen:**", "**Aclaracion:**"),
        "related_label": "**Conceptos utiles:**",
        "fallback_points_label": "**Lo mas importante:**",
        "summary_instruction": (
            "Explica como si hablaras con alguien que no conoce el tema. Prioriza claridad, ejemplos breves y lenguaje cotidiano."
        ),
        "llm_instruction": (
            "Usa un tono sencillo, cercano y personalizado, como una conversacion de tu a tu. "
            "Responde con seguridad y naturalidad. Evita expresiones como 'el documento dice', "
            "'en base al documento' o 'la evidencia indica' dentro del cuerpo de la respuesta. "
            "No te quedes en una respuesta minima: explica un poco mas para que la persona entienda bien el tema."
        ),
        "length_instruction": (
            "Apunta a 2 o 3 parrafos claros. Primero responde directo y luego amplia con ejemplos, consecuencias o aclaraciones utiles."
        ),
    },
    "tecnico": {
        "label": "Tecnico",
        "sections": ("**Sintesis tecnica:**", "**Hallazgos tecnicos:**", "**Interpretacion tecnica:**", "**Observacion tecnica:**"),
        "related_label": "**Variables y conceptos:**",
        "fallback_points_label": "**Hallazgos rescatables:**",
        "summary_instruction": (
            "Resume con enfoque tecnico, resaltando procedimiento, condiciones, criterios y relaciones operativas."
        ),
        "llm_instruction": (
            "Usa un tono tecnico y preciso, pero redacta de manera directa. "
            "No desplaces la atencion al documento ni repitas frases como 'la evidencia recuperada' dentro de cada punto. "
            "Desarrolla la respuesta con criterios, condiciones, proceso y relaciones operativas cuando el tema lo permita."
        ),
        "length_instruction": (
            "Apunta a 3 parrafos compactos pero sustanciosos. Prioriza procedimiento, criterios tecnicos, variables y efectos practicos."
        ),
    },
}
class RAGService:
    def __init__(self, progress_callback=None, *, auto_initialize: bool = True, eager_embeddings: bool = True) -> None:
        self.progress_callback = progress_callback
        self.auto_initialize = auto_initialize
        self.eager_embeddings = eager_embeddings
        self.index: Any | None = None
        self.retriever = None
        self.indexed_files: list[str] = []
        self.chunk_cache: list[dict] = []
        self.index_stale = False
        self.index_detail = "Servicio listo"
        self.last_index_source = "startup"
        self.last_index_seconds = 0.0
        self.response_mode = "extractive"
        self.llm_provider = ""
        self.llm_model = ""
        self.deployment_mode = settings.deployment_target
        self.allow_reindex = settings.allow_runtime_reindex
        self.enable_vector_retrieval = settings.enable_vector_retrieval
        self.document_storage_backend = settings.document_storage_backend
        self.index_storage_backend = settings.index_storage_backend
        self.metadata_backend = settings.metadata_backend
        self.process_state_backend = settings.process_state_backend
        self.documents_bucket = settings.documents_bucket
        self.indexes_bucket = settings.indexes_bucket
        self.active_index_name = settings.active_index_name
        self.runtime_storage_dir = settings.local_storage_dir
        self.runtime_state = metadata_repository.get_runtime_state()
        self.current_reindex_job_id = ""
        self.current_reindex_total_documents = 0
        self.current_reindex_processed_documents = 0
        self.current_reindex_total_units = 0
        self.current_reindex_completed_units = 0
        self.gemini_client = None
        self.openai_client = None
        self.vector_backend_ready = False
        self.embed_model_name = EMBED_MODEL if self._should_prepare_vector_backend() else "lexical-only"
        self._manifest_cache: dict | None = None
        self._manifest_cache_signature: tuple[tuple[str, int, int], ...] | None = None
        self._current_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        self.last_interaction_label = "Sin consultas"
        self.last_response_ms = 0
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.last_total_tokens = 0
        self.last_generation_status = "not_used"
        self.last_generation_error = ""
        self.last_generation_model = ""
        self._report_progress(5, "starting", "Preparando configuracion del servicio...")
        self._configure_llm_client()
        if self.eager_embeddings:
            self._report_progress(18, "embedding-setup", "Configurando el backend de embeddings...")
            self._configure_embeddings()
        if self.auto_initialize:
            self._report_progress(32, "index-check", "Verificando el indice documental...")
            self.ensure_index_ready()
            self._report_progress(100, "ready", "Servicio listo")

    def _report_progress(self, progress: int, stage: str, detail: str) -> None:
        if self.current_reindex_job_id:
            metadata_repository.update_reindex_progress(
                self.current_reindex_job_id,
                progress=progress,
                stage=stage,
                detail=detail,
                total_documents=self.current_reindex_total_documents,
                processed_documents=self.current_reindex_processed_documents,
            )
            self.runtime_state = metadata_repository.get_runtime_state()
        if self.progress_callback is not None:
            self.progress_callback(progress, stage, detail)

    def _begin_reindex_progress(self, total_documents: int) -> None:
        input_units = total_documents if self.document_storage_backend == "gcs" else 1
        self.current_reindex_total_units = max(1, total_documents + input_units + 5)
        self.current_reindex_completed_units = 0

    def _set_reindex_progress(
        self,
        *,
        stage: str,
        detail: str,
        default_progress: int,
        completed_units: int | None = None,
        increment_units: int = 0,
    ) -> None:
        if self.current_reindex_job_id and self.current_reindex_total_units > 0:
            if completed_units is not None:
                self.current_reindex_completed_units = max(
                    0,
                    min(completed_units, self.current_reindex_total_units),
                )
            elif increment_units:
                self.current_reindex_completed_units = max(
                    0,
                    min(
                        self.current_reindex_completed_units + increment_units,
                        self.current_reindex_total_units,
                    ),
                )

            real_progress = round(
                (self.current_reindex_completed_units / self.current_reindex_total_units) * 100
            )
            self._report_progress(real_progress, stage, detail)
            return

        self._report_progress(default_progress, stage, detail)

    def _configure_llm_client(self) -> None:
        gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if gemini_api_key:
            try:
                from google import genai

                self.gemini_client = genai.Client(api_key=gemini_api_key)
                self.response_mode = "generative-rag"
                self.llm_provider = "gemini"
                self.llm_model = GEMINI_MODEL
            except Exception:
                self.gemini_client = None
            return

        if api_key:
            try:
                from openai import OpenAI

                self.openai_client = OpenAI(api_key=api_key)
                self.response_mode = "generative-rag"
                self.llm_provider = "openai"
                self.llm_model = OPENAI_MODEL
            except Exception:
                self.openai_client = None

    def _configure_embeddings(self, *, force: bool = False) -> None:
        if self.vector_backend_ready:
            return
        if not self._should_prepare_vector_backend(force=force):
            self.vector_backend_ready = False
            self.embed_model_name = "lexical-only"
            return

        try:
            from llama_index.core import Settings
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding

            Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
            self.vector_backend_ready = True
            self.embed_model_name = EMBED_MODEL
        except Exception as exc:
            self.vector_backend_ready = False
            self.embed_model_name = "lexical-only"
            if self.deployment_mode == "local" and not self._has_chunk_cache():
                raise RuntimeError(
                    "No fue posible cargar el modelo de embeddings. "
                    "Si es la primera ejecucion, verifica tu conexion a internet para descargar el modelo "
                    f"'{EMBED_MODEL}'. Detalle original: {exc}"
                ) from exc

    def _ensure_embeddings_ready(self, *, force: bool = False) -> None:
        if self.vector_backend_ready or not self._should_prepare_vector_backend(force=force):
            return
        self._set_reindex_progress(
            stage="embedding-setup",
            detail="Configurando el backend de embeddings...",
            default_progress=18,
            increment_units=1,
        )
        self._configure_embeddings(force=force)

    def ensure_index_ready(self, force_rebuild: bool = False) -> None:
        started_at = time.perf_counter()
        self._report_progress(
            38 if not force_rebuild else 22,
            "index-loading",
            "Cargando el indice documental...",
        )
        self.index = self._load_or_build_index(force_rebuild=force_rebuild)
        self.retriever = (
            self.index.as_retriever(similarity_top_k=TOP_K)
            if self.index is not None
            else None
        )
        self.last_index_seconds = round(time.perf_counter() - started_at, 2)

    def _load_or_build_index(self, force_rebuild: bool = False) -> Any | None:
        materialized = index_repository.prepare_runtime_storage(self.embed_model_name)
        self.runtime_storage_dir = materialized.storage_dir
        self._set_reindex_progress(
            stage="manifest-scan",
            detail="Analizando documentos y archivos del indice...",
            default_progress=42,
            increment_units=1,
        )
        current_manifest = self._build_manifest()
        self.indexed_files = [item.file_name for item in current_manifest.files]

        if (
            not force_rebuild
            and self._can_boot_from_chunk_cache_only()
            and materialized.manifest == current_manifest
        ):
            self._report_progress(72, "chunk-cache", "Cargando indice desde chunk cache...")
            self.chunk_cache = materialized.chunk_cache
            self.index_stale = False
            self.index_detail = "Servicio listo"
            self.last_index_source = "chunk-cache"
            return None

        if not current_manifest.files:
            if index_repository.has_materialized_index():
                self._report_progress(72, "chunk-cache", "Cargando indice previamente almacenado...")
                self.chunk_cache = materialized.chunk_cache
                self.last_index_source = "chunk-cache"
                if not self.indexed_files:
                    self.indexed_files = [item.file_name for item in materialized.manifest.files]
                self.index_stale = False
                self.index_detail = "Servicio listo"
                return None

            raise RuntimeError(
                f"No se encontraron archivos PDF en {self._document_source_label()} ni un chunk_cache utilizable en backend/storage."
            )

        if not force_rebuild and self._has_usable_persisted_index(current_manifest):
            from llama_index.core import StorageContext, load_index_from_storage

            self._report_progress(78, "storage-index", "Cargando indice persistido...")
            storage_context = StorageContext.from_defaults(persist_dir=str(self.runtime_storage_dir))
            self.chunk_cache = materialized.chunk_cache
            self.index_stale = False
            self.index_detail = "Servicio listo"
            self.last_index_source = "storage"
            return load_index_from_storage(storage_context)

        if self.deployment_mode != "local" and not self.allow_reindex and not force_rebuild:
            if index_repository.has_materialized_index():
                self.chunk_cache = materialized.chunk_cache
                self.index_stale = True
                self.index_detail = (
                    f"Se detectaron cambios en {self._document_source_label()}, pero este despliegue no puede reindexar en vivo. "
                    "Reconstruye backend/storage localmente y vuelve a desplegar."
                )
                self.last_index_source = "chunk-cache"
                return None

            raise RuntimeError(
                "No se encontro un indice persistido utilizable para este despliegue. "
                "En Vercel debes incluir backend/storage actualizado en el repositorio o habilitar ALLOW_RUNTIME_REINDEX."
            )

        if not self.vector_backend_ready:
            self._ensure_embeddings_ready(force=force_rebuild)
        if not self.vector_backend_ready:
            raise RuntimeError(
                "No fue posible cargar el backend de embeddings necesario para reconstruir el indice."
            )

        self._set_reindex_progress(
            stage="document-load",
            detail="Preparando documentos PDF para reconstruir el indice...",
            default_progress=55,
        )
        documents = self._load_documents(current_manifest.files)
        from llama_index.core import VectorStoreIndex
        from llama_index.core.node_parser import SentenceSplitter

        self._set_reindex_progress(
            stage="node-build",
            detail="Dividiendo documentos en fragmentos analizables...",
            default_progress=68,
            increment_units=1,
        )
        splitter = SentenceSplitter(chunk_size=700, chunk_overlap=120)
        nodes = splitter.get_nodes_from_documents(documents)
        self._set_reindex_progress(
            stage="vector-index",
            detail=f"Construyendo el indice vectorial con {len(nodes)} fragmentos...",
            default_progress=82,
            increment_units=1,
        )
        self.chunk_cache = self._serialize_nodes(nodes)
        index = VectorStoreIndex(nodes)
        build_dir = index_repository.get_build_dir()
        self._set_reindex_progress(
            stage="persist-index",
            detail="Guardando el indice para futuros arranques...",
            default_progress=92,
            increment_units=1,
        )
        index.storage_context.persist(persist_dir=str(build_dir))
        self.index_stale = False
        self.index_detail = "Servicio listo"
        self.last_index_source = "rebuild"
        pointer = index_repository.finalize_rebuild(build_dir, current_manifest, self.chunk_cache, source="rebuild")
        metadata_repository.sync_documents(
            current_manifest,
            settings.documents_prefix,
            corpus_analysis=self._build_corpus_analysis(),
        )
        metadata_repository.update_active_index(
            pointer=pointer,
            manifest=current_manifest,
            source=self.index_storage_backend,
            job_id=self.current_reindex_job_id,
            status="success",
        )
        self.runtime_state = metadata_repository.get_runtime_state()
        self.runtime_storage_dir = index_repository.get_runtime_storage_dir()
        return index

    def _load_documents(self, manifest_files) -> list:
        from llama_index.core import SimpleDirectoryReader

        total_documents = len(manifest_files)
        input_preparation_base = self.current_reindex_completed_units

        def _input_preparation_progress(completed: int, total: int, relative_path: str) -> None:
            detail = (
                f"Preparando archivo {completed}/{total}: {Path(relative_path).name}"
                if total > 0
                else "Preparando documentos para el reindexado..."
            )
            self._set_reindex_progress(
                stage="document-cache",
                detail=detail,
                default_progress=55,
                completed_units=input_preparation_base + completed,
            )

        input_dir = document_repository.prepare_input_dir(progress_callback=_input_preparation_progress)
        if self.document_storage_backend != "gcs":
            self._set_reindex_progress(
                stage="document-cache",
                detail="Documentos locales listos para lectura.",
                default_progress=55,
                completed_units=input_preparation_base + 1,
            )

        parse_base = self.current_reindex_completed_units
        documents = []
        pdf_paths = sorted(input_dir.rglob("*.pdf"))
        total_paths = len(pdf_paths)

        for index, path in enumerate(pdf_paths, start=1):
            documents.extend(
                SimpleDirectoryReader(
                    input_files=[str(path)],
                    filename_as_id=True,
                ).load_data()
            )
            self.current_reindex_processed_documents = index
            self._set_reindex_progress(
                stage="document-load",
                detail=f"Leyendo documento {index}/{total_paths}: {path.name}",
                default_progress=55,
                completed_units=parse_base + index,
            )

        if total_documents == 0:
            self._set_reindex_progress(
                stage="document-load",
                detail="No hay documentos para procesar.",
                default_progress=55,
            )

        return documents

    def _has_chunk_cache(self) -> bool:
        return index_repository.has_materialized_index()

    def _should_prepare_vector_backend(self, *, force: bool = False) -> bool:
        return force or self.enable_vector_retrieval or self.allow_reindex

    def _can_boot_from_chunk_cache_only(self) -> bool:
        return self._has_chunk_cache() and not self._should_prepare_vector_backend()

    def _read_manifest(self) -> IndexManifest:
        return index_repository.prepare_runtime_storage(self.embed_model_name).manifest

    def _read_chunk_cache(self) -> list[dict]:
        return index_repository.prepare_runtime_storage(self.embed_model_name).chunk_cache

    def _has_usable_persisted_index(self, current_manifest: IndexManifest) -> bool:
        if not self.vector_backend_ready:
            return False

        if not index_repository.has_required_storage_files() or not index_repository.has_materialized_index():
            return False

        stored_manifest = self._read_manifest()
        return self._manifests_equivalent(stored_manifest, current_manifest)

    def _build_manifest(self) -> IndexManifest:
        file_entries = document_repository.list_pdf_files()
        cache_signature = tuple(
            (item.relative_path, int(item.size), item.fingerprint)
            for item in file_entries
        )
        if (
            self._manifest_cache is not None
            and self._manifest_cache_signature == cache_signature
        ):
            return self._manifest_cache

        files = tuple(sorted(file_entries, key=lambda item: item.relative_path))
        manifest = IndexManifest(
            manifest_version=2,
            embed_model=EMBED_MODEL,
            files=files,
        )
        self._manifest_cache_signature = cache_signature
        self._manifest_cache = manifest
        return manifest

    def _manifest_file_names(self, manifest: IndexManifest) -> list[str]:
        return [item.file_name for item in manifest.files]

    def _manifests_equivalent(self, stored_manifest: IndexManifest, current_manifest: IndexManifest) -> bool:
        if stored_manifest.embed_model != current_manifest.embed_model:
            return False

        stored_files = sorted(stored_manifest.files, key=lambda item: item.relative_path)
        current_files = sorted(current_manifest.files, key=lambda item: item.relative_path)
        if len(stored_files) != len(current_files):
            return False

        strict_compare = (
            stored_manifest.manifest_version == 2
            and current_manifest.manifest_version == 2
        )

        for stored_item, current_item in zip(stored_files, current_files):
            if stored_item.relative_path != current_item.relative_path:
                return False
            if int(stored_item.size) != int(current_item.size):
                return False
            if strict_compare and stored_item.fingerprint != current_item.fingerprint:
                return False

        return True

    def _refresh_index_if_needed(self) -> None:
        current_manifest = self._build_manifest()
        stored_manifest = self._read_manifest()
        has_changes = not self._manifests_equivalent(stored_manifest, current_manifest)

        current_files = self._manifest_file_names(current_manifest)
        stored_files = self._manifest_file_names(stored_manifest)
        self.indexed_files = current_files

        if not has_changes:
            self.index_stale = False
            self.index_detail = "Servicio listo"
            return

        self.index_stale = True
        self.indexed_files = stored_files
        self.index_detail = (
            f"Se detectaron {len(current_files)} PDFs en {self._document_source_label()}, pero solo {len(stored_files)} "
            "estan realmente indexados en backend/storage. "
            "Ejecuta el reindexado manual desde el panel de gestion documental."
        )

    def get_status(self) -> dict:
        self._refresh_index_if_needed()
        self.runtime_state = metadata_repository.get_runtime_state()
        if bool(self.chunk_cache) and not self.index_stale and self.runtime_state.last_reindex_status != "success":
            metadata_repository.reconcile_runtime_success()
            self.runtime_state = metadata_repository.get_runtime_state()
        return {
            "status": "ok",
            "detail": self.index_detail,
            "init_stage": "ready",
            "init_progress": 100,
            "indexed_files": self.indexed_files,
            "indexed_documents": self._indexed_documents_payload(),
            "indexed_file_count": len(self.indexed_files),
            "index_ready": bool(self.chunk_cache) and not self.index_stale,
            "index_source": self.last_index_source,
            "last_index_seconds": self.last_index_seconds,
            "embed_model": self.embed_model_name,
            "response_mode": self.response_mode,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "deployment_mode": self.deployment_mode,
            "allow_reindex": self.allow_reindex,
            "enable_vector_retrieval": self.enable_vector_retrieval,
            "document_storage_backend": self.document_storage_backend,
            "index_storage_backend": self.index_storage_backend,
            "metadata_backend": self.metadata_backend,
            "process_state_backend": self.process_state_backend,
            "documents_bucket": self.documents_bucket,
            "indexes_bucket": self.indexes_bucket,
            "active_index_name": self.active_index_name,
            "runtime_active_index_name": self.runtime_state.active_index_name,
            "runtime_active_index_source": self.runtime_state.active_index_source,
            "runtime_last_reindex_status": self.runtime_state.last_reindex_status,
            "runtime_last_reindex_job_id": self.runtime_state.last_reindex_job_id,
            "runtime_reindex_progress": self.runtime_state.reindex_progress,
            "runtime_reindex_stage": self.runtime_state.reindex_stage,
            "runtime_reindex_detail": self.runtime_state.reindex_detail,
            "runtime_reindex_total_documents": self.runtime_state.reindex_total_documents,
            "runtime_reindex_processed_documents": self.runtime_state.reindex_processed_documents,
            "frequent_questions": self.runtime_state.frequent_questions,
            "last_interaction_label": self.last_interaction_label,
            "last_response_ms": self.last_response_ms,
            "last_input_tokens": self.last_input_tokens,
            "last_output_tokens": self.last_output_tokens,
            "last_total_tokens": self.last_total_tokens,
            "last_generation_status": self.last_generation_status,
            "last_generation_error": self.last_generation_error,
            "last_generation_model": self.last_generation_model,
        }

    def reindex(self) -> dict:
        current_manifest = self._build_manifest()
        stored_manifest = self._read_manifest()
        self.indexed_files = self._manifest_file_names(current_manifest)

        if (
            self._manifests_equivalent(stored_manifest, current_manifest)
            and index_repository.has_materialized_index()
            and index_repository.has_required_storage_files()
        ):
            self.chunk_cache = self._read_chunk_cache()
            self.index_stale = False
            self.index_detail = "El indice ya estaba actualizado. No fue necesario reconstruirlo."
            self.last_index_source = "storage"
            self.runtime_state = metadata_repository.get_runtime_state()
            return {
                "status": "ok",
                "detail": self.index_detail,
                "indexed_files": self.indexed_files,
                "indexed_documents": self._indexed_documents_payload(),
                "index_source": self.last_index_source,
                "last_index_seconds": 0.0,
            }

        self.current_reindex_total_documents = len(current_manifest.files)
        self.current_reindex_processed_documents = 0
        self._begin_reindex_progress(self.current_reindex_total_documents)
        job_id = metadata_repository.start_reindex_job(
            trigger="api",
            source=self.deployment_mode,
            total_documents=self.current_reindex_total_documents,
        )
        self.current_reindex_job_id = job_id
        try:
            self._ensure_embeddings_ready(force=True)
            self.ensure_index_ready(force_rebuild=True)
        except Exception as exc:
            metadata_repository.finish_reindex_job(
                job_id,
                status="failed",
                error_message=str(exc),
            )
            self.runtime_state = metadata_repository.get_runtime_state()
            self.current_reindex_job_id = ""
            self.current_reindex_total_documents = 0
            self.current_reindex_processed_documents = 0
            self.current_reindex_total_units = 0
            self.current_reindex_completed_units = 0
            raise

        metadata_repository.finish_reindex_job(
            job_id,
            status="success",
            release_name=self.runtime_state.active_index_name or self.active_index_name,
        )
        self.runtime_state = metadata_repository.get_runtime_state()
        self.current_reindex_job_id = ""
        self.current_reindex_total_documents = 0
        self.current_reindex_processed_documents = 0
        self.current_reindex_total_units = 0
        self.current_reindex_completed_units = 0
        return {
            "status": "ok",
            "detail": "Indice reconstruido correctamente",
            "indexed_files": self.indexed_files,
            "indexed_documents": self._indexed_documents_payload(),
            "index_source": self.last_index_source,
            "last_index_seconds": self.last_index_seconds,
        }

    def query(
        self,
        question: str,
        history: list[dict] | None = None,
        response_style: str = "academico",
    ) -> dict:
        started_at = time.perf_counter()
        self._reset_current_usage()
        self._refresh_index_if_needed()
        if not self.chunk_cache:
            raise RuntimeError("El indice documental aun no esta listo.")
        if self.index_stale:
            raise RuntimeError(self.index_detail)
        metadata_repository.record_question(question)
        self.runtime_state = metadata_repository.get_runtime_state()

        small_talk_answer = self._small_talk_answer(question)
        if small_talk_answer:
            result = {
                "answer": small_talk_answer,
                "found": True,
                "sources": [],
            }
            self._record_interaction_metrics("Ultima respuesta", started_at)
            return {**result, **self._current_response_metrics()}

        document_count_answer = self._document_count_answer(question)
        if document_count_answer:
            result = {
                "answer": document_count_answer,
                "found": True,
                "sources": [],
            }
            self._record_interaction_metrics("Ultima respuesta", started_at)
            return {**result, **self._current_response_metrics()}

        keywords = self._extract_keywords(question)
        vector_candidates = self._vector_candidates(question, keywords)
        lexical_candidates = self._lexical_candidates(keywords)
        merged_candidates = self._merge_candidates(vector_candidates, lexical_candidates)

        filtered_nodes = [
            item for item in merged_candidates if item["keyword_overlap"] > 0
        ] or merged_candidates[:MAX_RESPONSE_EVIDENCE]

        if not filtered_nodes:
            result = {
                "answer": (
                    "No se encontro informacion suficiente en los documentos cargados "
                    "para responder esa pregunta."
                ),
                "found": False,
                "sources": [],
            }
            self._record_interaction_metrics("Ultima respuesta", started_at)
            return {**result, **self._current_response_metrics()}

        source_chunks = []
        evidence_blocks = []

        for item in filtered_nodes[:MAX_RESPONSE_EVIDENCE]:
            file_name = item["file_name"]
            page_label = item.get("page_label", "")
            normalized_text = self._clean_ocr_text(item["text"])
            excerpt = normalized_text[:MAX_RESPONSE_SOURCE_EXCERPT]
            score = item["score"]

            source_chunks.append(
                {
                    "file_name": file_name,
                    "display_title": self._display_title(file_name),
                    "page_label": page_label,
                    "score": score,
                    "text": excerpt,
                }
            )
            evidence_blocks.append((file_name, page_label, score, normalized_text))

        if not any(item["keyword_overlap"] > 0 for item in filtered_nodes):
            result = {
                "answer": (
                    "No se encontro informacion suficientemente relacionada con la pregunta "
                    "dentro de los documentos cargados."
                ),
                "found": False,
                "sources": [],
            }
            self._record_interaction_metrics("Ultima respuesta", started_at)
            return {**result, **self._current_response_metrics()}

        answer = self._compose_answer(
            question,
            evidence_blocks,
            history or [],
            response_style=response_style,
        )

        result = {
            "answer": answer,
            "found": True,
            "sources": source_chunks,
        }
        self._record_interaction_metrics("Ultima respuesta", started_at)
        return {**result, **self._current_response_metrics()}

    def summarize_document(self, file_name: str, response_style: str = "academico") -> dict:
        started_at = time.perf_counter()
        self._reset_current_usage()
        self._refresh_index_if_needed()
        if self.index_stale:
            raise RuntimeError(self.index_detail)
        matching_chunks = [
            chunk for chunk in self.chunk_cache if chunk["file_name"].strip().lower() == file_name.strip().lower()
        ]
        if not matching_chunks:
            raise ValueError(f"No se encontro un documento llamado '{file_name}'.")

        selected_chunks = self._select_summary_chunks(matching_chunks)
        sources = [
            {
                "file_name": chunk["file_name"],
                "display_title": self._display_title(chunk["file_name"]),
                "page_label": chunk.get("page_label", ""),
                "score": 1.0,
                "text": self._clean_ocr_text(chunk["text"])[:650],
            }
            for chunk in selected_chunks[:4]
        ]
        evidence_blocks = [
            (
                chunk["file_name"],
                chunk.get("page_label", ""),
                1.0,
                self._clean_ocr_text(chunk["text"]),
            )
            for chunk in selected_chunks[:5]
        ]

        style_config = self._style_config(response_style)
        prompt = (
            f"Resume el documento '{selected_chunks[0]['file_name']}' de forma organizada.\n"
            "Debes escribir en espanol, sin copiar el texto literalmente.\n"
            f"{style_config['summary_instruction']}\n"
            "Responde con un resumen fluido, natural y facil de seguir, sin encabezados como Resumen, Puntos clave o Conclusion.\n"
            "Usa listas con guiones solo cuando realmente aporten claridad.\n"
            "Si puedes, incorpora de forma natural las partes mas utiles del documento sin cerrar con una seccion de referencias.\n"
        )
        answer = self._compose_answer(
            prompt,
            evidence_blocks,
            history=[],
            response_style=response_style,
        )
        result = {
            "file_name": selected_chunks[0]["file_name"],
            "display_title": self._display_title(selected_chunks[0]["file_name"]),
            "answer": answer,
            "found": True,
            "sources": sources,
        }
        self._record_interaction_metrics("Ultimo resumen", started_at)
        return {**result, **self._current_response_metrics()}

    def _small_talk_answer(self, question: str) -> str:
        normalized_question = " ".join(question.strip().split())
        for pattern, answer in SMALL_TALK_PATTERNS:
            if pattern.match(normalized_question):
                return answer
        return ""

    def _document_count_answer(self, question: str) -> str:
        normalized_question = " ".join(question.strip().split())
        if not any(pattern.match(normalized_question) for pattern in DOCUMENT_COUNT_PATTERNS):
            return ""

        total_documents = len(self.indexed_files)
        document_label = "documento" if total_documents == 1 else "documentos"
        return (
            f"Actualmente tengo {total_documents} {document_label} indexados y listos para consulta."
        )

    def _vector_candidates(self, question: str, keywords: set[str]) -> list[dict]:
        if self.retriever is None:
            return []

        ranked_nodes = []

        for node in self.retriever.retrieve(question):
            if node.score is None or float(node.score) < SIMILARITY_THRESHOLD:
                continue

            normalized_text = " ".join(node.text.strip().split())
            ranked_nodes.append(
                {
                    "file_name": self._node_file_name(node.metadata or {}),
                    "page_label": self._node_page_label(node.metadata or {}),
                    "text": normalized_text,
                    "keyword_overlap": len(self._normalize_tokens(normalized_text) & keywords),
                    "score": round(float(node.score), 4),
                }
            )

        return ranked_nodes

    def _lexical_candidates(self, keywords: set[str]) -> list[dict]:
        if not keywords:
            return []

        candidates = []

        for chunk in self.chunk_cache:
            overlap = len(set(chunk["tokens"]) & keywords)
            if overlap == 0:
                continue

            candidates.append(
                {
                    "file_name": chunk["file_name"],
                    "page_label": chunk.get("page_label", ""),
                    "text": chunk["text"],
                    "keyword_overlap": overlap,
                    "score": round(min(0.99, 0.2 + overlap * 0.12), 4),
                }
            )

        candidates.sort(
            key=lambda item: (item["keyword_overlap"], item["score"], len(item["text"])),
            reverse=True,
        )
        return candidates[:6]

    def _merge_candidates(self, vector_candidates: list[dict], lexical_candidates: list[dict]) -> list[dict]:
        merged: dict[tuple[str, str], dict] = {}

        for candidate in [*vector_candidates, *lexical_candidates]:
            key = (candidate["file_name"], candidate.get("page_label", ""), candidate["text"][:220])
            current = merged.get(key)
            if current is None:
                merged[key] = candidate
                continue

            current["keyword_overlap"] = max(current["keyword_overlap"], candidate["keyword_overlap"])
            current["score"] = max(current["score"], candidate["score"])

        ranked = sorted(
            merged.values(),
            key=lambda item: (item["keyword_overlap"], item["score"], len(item["text"])),
            reverse=True,
        )
        return ranked[:6]

    def _serialize_nodes(self, nodes: list) -> list[dict]:
        serialized = []

        for node in nodes:
            metadata = node.metadata or {}
            text = " ".join(node.text.strip().split())
            if not text:
                continue

            serialized.append(
                ChunkCacheEntry(
                    file_name=self._node_file_name(metadata),
                    page_label=self._node_page_label(metadata),
                    text=text,
                    tokens=tuple(sorted(self._normalize_tokens(text))),
                ).to_dict()
            )

        return serialized

    def _build_corpus_analysis(self) -> dict[str, dict]:
        chunks_by_file: dict[str, list[str]] = {}
        path_by_file_name = {
            item.file_name: item.relative_path
            for item in self._build_manifest().files
        }

        for chunk in self.chunk_cache:
            file_name = chunk.get("file_name", "")
            text = chunk.get("text", "")
            if not file_name or not text:
                continue
            chunks_by_file.setdefault(file_name, []).append(text)

        analysis_by_path: dict[str, dict] = {}
        for file_name, chunks in chunks_by_file.items():
            relative_path = path_by_file_name.get(file_name, file_name)
            analysis_by_path[relative_path] = analyze_corpus_document(file_name, chunks[:12])

        return analysis_by_path

    def cloud_index_contract(self) -> dict:
        release_example = "YYYYMMDD-HHMMSS"
        return {
            "documents_bucket": self.documents_bucket,
            "indexes_bucket": self.indexes_bucket,
            "active_index_name": self.active_index_name,
            "document_example_blob": cloud_layout.document_blob_path("carpeta/documento.pdf"),
            "active_pointer_blob": cloud_layout.active_index_pointer_blob(),
            "release_prefix_example": cloud_layout.index_release_prefix(release_example),
            "release_manifest_blob_example": cloud_layout.release_manifest_blob(release_example),
            "release_chunk_cache_blob_example": cloud_layout.release_chunk_cache_blob(release_example),
            "firestore_documents_collection": settings.firestore_documents_collection,
            "firestore_jobs_collection": settings.firestore_jobs_collection,
            "firestore_runtime_collection": settings.firestore_runtime_collection,
        }

    def _node_file_name(self, metadata: dict) -> str:
        return metadata.get("file_name") or metadata.get("filename") or "Documento"

    def _node_page_label(self, metadata: dict) -> str:
        return str(metadata.get("page_label") or metadata.get("page") or "")

    def _indexed_documents_payload(self) -> list[dict]:
        return [
            {
                "file_name": file_name,
                "display_title": self._display_title(file_name),
            }
            for file_name in self.indexed_files
        ]

    def _reset_current_usage(self) -> None:
        self._current_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def _record_interaction_metrics(self, label: str, started_at: float) -> None:
        self.last_interaction_label = label
        self.last_response_ms = int((time.perf_counter() - started_at) * 1000)
        self.last_input_tokens = int(self._current_usage.get("input_tokens", 0) or 0)
        self.last_output_tokens = int(self._current_usage.get("output_tokens", 0) or 0)
        self.last_total_tokens = int(self._current_usage.get("total_tokens", 0) or 0)

    def _current_response_metrics(self) -> dict:
        return {
            "response_ms": self.last_response_ms,
            "input_tokens": self.last_input_tokens,
            "output_tokens": self.last_output_tokens,
            "total_tokens": self.last_total_tokens,
        }

    def _capture_usage(self, response: Any) -> None:
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            prompt = int(getattr(usage, "prompt_token_count", 0) or 0)
            candidates = int(getattr(usage, "candidates_token_count", 0) or 0)
            total = int(getattr(usage, "total_token_count", prompt + candidates) or 0)
            self._current_usage = {
                "input_tokens": prompt,
                "output_tokens": candidates,
                "total_tokens": total,
            }
            return

        usage = getattr(response, "usage", None)
        if usage is not None:
            prompt = int(getattr(usage, "input_tokens", 0) or 0)
            completion = int(getattr(usage, "output_tokens", 0) or 0)
            total = int(getattr(usage, "total_tokens", prompt + completion) or 0)
            self._current_usage = {
                "input_tokens": prompt,
                "output_tokens": completion,
                "total_tokens": total,
            }

    def _display_title(self, file_name: str) -> str:
        stem = Path(file_name).stem.strip()
        cleaned = self._repair_mojibake(stem)
        signature = re.sub(r"[^a-z0-9]+", "", self._normalize_text(cleaned))
        lowered_stem = stem.lower()

        if "agroecologiaenelecuadorprocesohistoricologrosydesa" in signature:
            return "Agroecologia en el Ecuador: proceso historico, logros y desafios"
        if signature.startswith("dialnetlarevalorizaciondelaidentidadcultural"):
            return "La revalorizacion de la identidad cultural"
        if signature.startswith("dialnetsaberesancestrales"):
            return "Saberes ancestrales"
        if signature.startswith("e11modulosaberesancestrales"):
            return "Modulo de saberes ancestrales"
        if signature.startswith("estudiosaberesancestrales"):
            return "Estudio de saberes ancestrales"
        if signature == "papa":
            return "Papa"
        if "resumenejecutivodiagnosticosterritorialesdelsectoragrario" in signature:
            return "Resumen ejecutivo de diagnosticos territoriales del sector agrario"
        if "resumen-ejecutivo" in lowered_stem and "sector-agrario" in lowered_stem:
            return "Resumen ejecutivo de diagnosticos territoriales del sector agrario"

        cleaned = cleaned.replace("_", " ")
        cleaned = re.sub(r"\+", " ", cleaned)
        cleaned = re.sub(r"%20", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b\d{1,2}(?:[-_/]\d{1,2}){2,}\b", "", cleaned)
        cleaned = re.sub(r"\b\d{6,}\b$", "", cleaned)
        cleaned = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cleaned)
        cleaned = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", cleaned)

        if cleaned.lower().startswith("dialnet-"):
            cleaned = cleaned[8:]
        if cleaned.lower().startswith("editum,"):
            cleaned = cleaned[7:]

        cleaned = re.sub(r"\bcap(?:itulo)?\s*\d+\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bcompressed\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bweb[- ]?sp\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[-_]{2,}", " ", cleaned)
        cleaned = re.sub(r"[-_]", " ", cleaned)
        cleaned = re.sub(r"\b\d+\b$", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_,.;:")

        if not cleaned:
            return file_name

        return self._title_case_spanish(cleaned)

    def _document_source_label(self) -> str:
        return document_repository.describe_source()

    def _repair_mojibake(self, text: str) -> str:
        cleaned = unicodedata.normalize("NFKC", text)
        replacements = {
            "Â¦": "",
            "Ã¼": "u",
            "Ã¡": "a",
            "Ã©": "e",
            "Ã­": "i",
            "Ã³": "o",
            "Ãº": "u",
            "Ã±": "n",
        }
        for source, target in replacements.items():
            cleaned = cleaned.replace(source, target)

        for _ in range(2):
            try:
                repaired = cleaned.encode("latin-1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                break
            if repaired == cleaned:
                break
            cleaned = repaired

        return cleaned

    def _title_case_spanish(self, text: str) -> str:
        small_words = {
            "a", "al", "con", "de", "del", "el", "en", "la", "las", "los",
            "para", "por", "un", "una", "y",
        }
        acronyms = {"PDF", "SP", "I", "II", "III", "IV", "V"}
        words = []

        for index, word in enumerate(text.split()):
            if word.upper() in acronyms:
                words.append(word.upper())
                continue

            lowered = word.lower()
            if index > 0 and lowered in small_words:
                words.append(lowered)
                continue

            if word.isupper() or re.search(r"[A-Z]{3,}", word):
                words.append(word.capitalize())
                continue

            words.append(word[:1].upper() + word[1:])

        title = " ".join(words)
        title = re.sub(r"\s+:\s+", ": ", title)
        return title.strip()

    def _compose_answer(
        self,
        question: str,
        evidence_blocks: list[tuple[str, str, float, str]],
        history: list[dict],
        response_style: str = "academico",
    ) -> str:
        style_config = self._style_config(response_style)
        if self.gemini_client is not None or self.openai_client is not None:
            generated_answer = self._generate_llm_answer(
                question,
                evidence_blocks,
                history,
                response_style=response_style,
            )
            if generated_answer:
                return generated_answer

        keywords = self._extract_keywords(question)
        insights = self._build_analysis_insights(evidence_blocks, keywords)

        if not insights:
            fallback_points = []
            for file_name, page_label, score, text in evidence_blocks[:3]:
                snippet = self._fallback_snippet(text)
                if not snippet:
                    continue
                fallback_points.append(f"- {snippet}")

            if not fallback_points:
                return (
                    "Encontre fragmentos relacionados, pero no suficiente contexto para elaborar "
                    "una respuesta clara sin arriesgar una interpretacion incorrecta."
                )

            return (
                "Encontre informacion relacionada, pero todavia no me alcanza para responder con la claridad que me gustaria.\n\n"
                + "\n".join(fallback_points)
                + "\n\nSi quieres, puedo afinar la busqueda con una pregunta mas especifica."
            )

        return self._compose_conversational_fallback(
            question,
            insights,
            keywords,
            response_style,
        )

    def _generate_llm_answer(
        self,
        question: str,
        evidence_blocks: list[tuple[str, str, float, str]],
        history: list[dict],
        response_style: str = "academico",
    ) -> str:
        style_config = self._style_config(response_style)
        self.last_generation_status = "attempted"
        self.last_generation_error = ""
        self.last_generation_model = ""
        evidence_text = self._format_evidence_for_llm(evidence_blocks)
        conversation_text = self._format_history_for_llm(history)
        prompt = (
            "Responde en espanol claro, natural y conversacional, como si hablaras con una persona.\n"
            "Sintetiza, conecta ideas y evita copiar frases largas o texto crudo del PDF.\n"
            "Si la evidencia no alcanza, dilo claramente. No inventes datos.\n"
            "La evidencia puede contener ruido OCR: palabras cortadas, guiones raros, numeros de pagina o fragmentos como 'evo- 178'. "
            "No reproduzcas esos artefactos; reconstruye la idea en tus propias palabras.\n"
            f"{style_config['llm_instruction']}\n"
            f"{style_config['length_instruction']}\n"
            "\n"
            "Historial reciente:\n"
            f"{conversation_text}\n\n"
            "Pregunta actual:\n"
            f"{question}\n\n"
            "Evidencia recuperada:\n"
            f"{evidence_text}\n\n"
            "Instrucciones de salida:\n"
            "1. Responde de forma directa, natural y segura, como una conversacion uno a uno.\n"
            "2. No uses encabezados como Respuesta breve, Puntos clave, Conclusion, Resumen o similares.\n"
            "3. No respondas de forma demasiado corta salvo que la pregunta sea extremadamente simple.\n"
            "4. Usa listas con guiones solo cuando realmente ayuden.\n"
            "5. Si hay limites o ambiguedades, explicalos con naturalidad dentro de la respuesta.\n"
            "6. No menciones de forma repetitiva que respondes en base a documentos. Las fuentes ya se mostraran aparte.\n"
            "7. No incluyas numeros sueltos, codigos de pagina, palabras incompletas ni cortes con guion.\n"
        )

        try:
            if self.gemini_client is not None:
                return self._generate_gemini_answer(prompt)

            response = self.openai_client.responses.create(model=self.llm_model, input=prompt)
            self._capture_usage(response)
        except Exception as exc:
            self.last_generation_status = "failed"
            self.last_generation_error = str(exc)[:300]
            return ""

        output_text = getattr(response, "output_text", "") or ""
        cleaned_output = self._clean_generated_answer(output_text)
        if cleaned_output:
            self.last_generation_status = "success"
            return cleaned_output
        self.last_generation_status = "empty"
        self.last_generation_error = "OpenAI devolvio una respuesta vacia."
        return ""

    def _generate_gemini_answer(self, prompt: str) -> str:
        model_candidates = [self.llm_model]
        if GEMINI_FALLBACK_MODEL and GEMINI_FALLBACK_MODEL not in model_candidates:
            model_candidates.append(GEMINI_FALLBACK_MODEL)

        last_error = ""
        for model_name in model_candidates:
            try:
                response = self._generate_gemini_with_timeout(model_name, prompt)
                self._capture_usage(response)
                output_text = getattr(response, "text", "") or ""
                cleaned_output = self._clean_generated_answer(output_text)
                self.last_generation_model = model_name
                if cleaned_output:
                    self.last_generation_status = "success"
                    return cleaned_output
                last_error = f"{model_name} devolvio una respuesta vacia."
            except Exception as exc:
                last_error = str(exc)[:300]
                if "503" not in last_error and "UNAVAILABLE" not in last_error.upper():
                    self.last_generation_model = model_name
                    self.last_generation_status = "failed"
                    self.last_generation_error = last_error
                    return ""

        self.last_generation_model = model_candidates[-1] if model_candidates else ""
        self.last_generation_status = "failed"
        self.last_generation_error = last_error or "Gemini no devolvio una respuesta util."
        return ""

    def _generate_gemini_with_timeout(self, model_name: str, prompt: str):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            self.gemini_client.models.generate_content,
            model=model_name,
            contents=prompt,
        )
        try:
            return future.result(timeout=LLM_TIMEOUT_SECONDS)
        except TimeoutError as exc:
            future.cancel()
            raise TimeoutError(
                f"{model_name} supero el limite de {LLM_TIMEOUT_SECONDS:.1f}s para mantener respuesta sub-3s."
            ) from exc
        finally:
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                executor.shutdown(wait=False)

    def _format_history_for_llm(self, history: list[dict]) -> str:
        if not history:
            return "Sin historial previo."

        lines = []
        for message in history[-6:]:
            role = "Usuario" if message.get("role") == "user" else "Asistente"
            content = " ".join(str(message.get("content", "")).split())
            if not content:
                continue
            lines.append(f"{role}: {content}")

        return "\n".join(lines) if lines else "Sin historial previo."

    def _format_evidence_for_llm(self, evidence_blocks: list[tuple[str, str, float, str]]) -> str:
        blocks = []
        for index, (file_name, page_label, score, text) in enumerate(
            evidence_blocks[:MAX_RESPONSE_EVIDENCE], start=1
        ):
            blocks.append(
                f"[Fuente {index}] Documento: {self._display_title(file_name)} | pagina: {page_label or 'sin pagina'} | relevancia: {score}\n{self._clean_ocr_text(text)[:MAX_LLM_EVIDENCE_CHARS]}"
            )
        return "\n\n".join(blocks)

    def _best_sentences_for_question(self, text: str, keywords: set[str]) -> list[str]:
        sentences = [
            self._clean_sentence(sentence)
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
            if len(self._clean_sentence(sentence)) >= 40
        ]

        ranked = sorted(
            sentences,
            key=lambda sentence: self._sentence_score(sentence, keywords),
            reverse=True,
        )
        return [
            sentence
            for sentence in ranked
            if self._sentence_score(sentence, keywords)[0] > 0
        ][:3]

    def _sentence_score(self, sentence: str, keywords: set[str]) -> tuple[int, int]:
        tokens = self._normalize_tokens(sentence)
        overlap = len(tokens & keywords)
        return overlap, len(sentence)

    def _build_analysis_insights(
        self, evidence_blocks: list[tuple[str, str, float, str]], keywords: set[str]
    ) -> list[dict]:
        insights: list[dict] = []
        seen = set()

        for file_name, page_label, score, text in evidence_blocks:
            best_sentences = self._best_sentences_for_question(text, keywords)
            if not best_sentences:
                continue

            merged_summary = self._merge_sentences(best_sentences[:2], keywords)
            summary = self._clean_summary(merged_summary)
            if not summary:
                continue

            signature = self._normalize_text(summary)
            if signature in seen:
                continue

            seen.add(signature)
            insights.append(
                {
                    "summary": summary,
                    "file_name": file_name,
                    "page_label": page_label,
                    "score": score,
                    "keywords": self._normalize_tokens(summary),
                }
            )

        insights.sort(
            key=lambda item: (
                len(item["keywords"] & keywords),
                item["score"],
                len(item["summary"]),
            ),
            reverse=True,
        )
        return insights

    def _merge_sentences(self, sentences: list[str], keywords: set[str]) -> str:
        clauses: list[str] = []

        for sentence in sentences:
            clauses.extend(self._ranked_clauses(sentence, keywords))

        unique_clauses = []
        seen = set()
        for clause in clauses:
            signature = self._normalize_text(clause)
            if signature in seen:
                continue
            seen.add(signature)
            unique_clauses.append(clause)
            if len(unique_clauses) == 2:
                break

        if not unique_clauses:
            return ""
        if len(unique_clauses) == 1:
            return self._to_analysis_sentence(unique_clauses[0])

        first_clause = self._clause_to_fragment(unique_clauses[0], preserve_case=True)
        second_clause = self._clause_to_fragment(unique_clauses[1], preserve_case=False)
        return f"{self._ensure_sentence(first_clause)} Ademas, {second_clause}."

    def _ranked_clauses(self, sentence: str, keywords: set[str]) -> list[str]:
        raw_clauses = [
            self._clean_sentence(part)
            for part in re.split(r"[;:()]|,\s+(?:y|pero|aunque|mientras|donde)\s+", sentence)
        ]
        filtered_clauses = [clause for clause in raw_clauses if len(clause) >= 30]
        ranked = sorted(
            filtered_clauses,
            key=lambda clause: self._sentence_score(clause, keywords),
            reverse=True,
        )
        return ranked[:3]

    def _to_analysis_sentence(self, clause: str) -> str:
        fragment = self._clause_to_fragment(clause, preserve_case=False)
        if not fragment:
            return ""
        return self._ensure_sentence(fragment[:1].upper() + fragment[1:])

    def _clause_to_fragment(self, clause: str, preserve_case: bool) -> str:
        fragment = self._clean_sentence(clause)
        fragment = re.sub(
            r"^(en\s+(?:los|las)\s+documentos?|los\s+documentos?|el\s+documento|segun\s+el\s+documento)\s+",
            "",
            fragment,
            flags=re.IGNORECASE,
        )
        fragment = re.sub(r"\s+", " ", fragment).strip(" .,:;")
        if not fragment:
            return ""
        if preserve_case:
            return fragment
        return fragment[:1].lower() + fragment[1:]

    def _clean_summary(self, summary: str) -> str:
        cleaned = self._clean_sentence(summary)
        if len(cleaned) < 35:
            return ""
        return cleaned

    def _build_overview(
        self,
        question: str,
        insights: list[dict],
        keywords: set[str],
        response_style: str,
    ) -> str:
        question_style = self._question_style(question)

        if response_style == "simple":
            if question_style == "como":
                base = "Asi se entiende o se aplica el tema que preguntaste"
            elif question_style == "por_que":
                base = "Esto ayuda a entender por que ocurre o por que se recomienda ese tema"
            elif question_style == "cuales":
                base = "Hay varios puntos concretos relacionados con tu pregunta"
            else:
                base = "Esto es lo mas importante para responderte"
        elif response_style == "tecnico":
            if question_style == "como":
                base = "El procedimiento o la aplicacion operativa del tema consultado se puede resumir asi"
            elif question_style == "por_que":
                base = "Los factores o fundamentos tecnicos asociados al tema consultado se pueden resumir asi"
            elif question_style == "cuales":
                base = "Los componentes, criterios o elementos tecnicos vinculados con la consulta son estos"
            else:
                base = "La respuesta puede sintetizarse asi, con enfoque tecnico"
        elif question_style == "como":
            base = "Asi ocurre o se aplica principalmente el tema consultado"
        elif question_style == "por_que":
            base = "Las causas o razones principales asociadas al tema consultado son estas"
        elif question_style == "cuales":
            base = "Se pueden identificar varios elementos concretos relacionados con tu pregunta"
        else:
            base = "Se puede responder de forma sintetizada asi"

        return f"{base}."

    def _build_extractive_overview(self, question: str, response_style: str) -> str:
        if response_style == "simple":
            return "Te lo explico de forma clara con lo que encontre."
        if response_style == "tecnico":
            return "Tecnicamente, esto es lo mas importante."
        return "Asi se entiende mejor la diferencia."

    def _compose_conversational_fallback(
        self,
        question: str,
        insights: list[dict],
        keywords: set[str],
        response_style: str,
    ) -> str:
        comparison_answer = self._domain_comparison_fallback(question, keywords)
        if comparison_answer:
            return comparison_answer

        summaries = [
            self._humanize_extractive_summary(insight["summary"], response_style)
            for insight in insights[:3]
        ]
        summaries = [summary for summary in summaries if summary]
        if not summaries:
            return (
                "Mira, encontre informacion relacionada, pero los fragmentos recuperados no son lo bastante claros "
                "como para darte una respuesta segura. Si quieres, prueba con una pregunta un poco mas especifica."
            )

        if response_style == "tecnico":
            intro = "Mira, tecnicamente lo mas importante es esto."
        elif response_style == "simple":
            intro = "Mira, te lo explico de forma sencilla."
        else:
            intro = "Mira, la idea principal es esta."

        if len(summaries) == 1:
            return f"{intro}\n\n{summaries[0]}"

        if response_style == "simple":
            return (
                f"{intro}\n\n"
                f"Primero, {self._lowercase_first(summaries[0])}\n\n"
                f"Ademas, {self._lowercase_first(summaries[1])}"
                + (
                    f"\n\nEso tambien ayuda a entender que {self._lowercase_first(summaries[2])}"
                    if len(summaries) > 2
                    else ""
                )
            )

        if response_style == "tecnico":
            return (
                f"{intro}\n\n"
                f"En primer lugar, {self._lowercase_first(summaries[0])}\n\n"
                f"En segundo lugar, {self._lowercase_first(summaries[1])}"
                + (
                    f"\n\nComo complemento tecnico, {self._lowercase_first(summaries[2])}"
                    if len(summaries) > 2
                    else ""
                )
            )

        return (
            f"{intro}\n\n"
            f"En primer lugar, {self._lowercase_first(summaries[0])}\n\n"
            f"Ademas, {self._lowercase_first(summaries[1])}"
            + (
                f"\n\nEsto tambien permite ver que {self._lowercase_first(summaries[2])}"
                if len(summaries) > 2
                else ""
            )
        )

    def _domain_comparison_fallback(self, question: str, keywords: set[str]) -> str:
        normalized_question = self._normalize_text(question)
        asks_difference = any(term in normalized_question for term in ("diferencia", "diferencias", "comparar", "versus", " vs "))
        traditional = "tradicional" in keywords or "campesina" in keywords or "campesino" in keywords
        ecological = "ecologica" in keywords or "ecologico" in keywords or "agroecologia" in keywords or "agroecologia" in normalized_question
        agriculture = "agricultura" in keywords or "agricola" in keywords

        if not (asks_difference and traditional and ecological and agriculture):
            return ""

        return (
            "Mira, la diferencia principal es esta: la agricultura tradicional nace de las practicas que las comunidades ya han construido con el tiempo, "
            "mientras que la agricultura ecologica toma muchas de esas bases y las organiza con una intencion mas clara de sostenibilidad.\n\n"
            "La agricultura tradicional o campesina se apoya mucho en el conocimiento local, en la experiencia acumulada, en los recursos disponibles del territorio "
            "y en la necesidad de sostener la alimentacion y la vida de la familia o la comunidad. No siempre aparece como una teoria formal, sino como una forma de producir aprendida y adaptada al lugar.\n\n"
            "La agricultura ecologica, en cambio, busca producir cuidando de manera mas consciente el suelo, el agua, la biodiversidad y la continuidad del sistema productivo. "
            "Puede incorporar conocimientos tradicionales, pero tambien los combina con criterios tecnicos, agroecologicos y ambientales para conservar recursos y mantener la productividad en el tiempo.\n\n"
            "En pocas palabras: la agricultura tradicional es la base cultural y practica; la agricultura ecologica es un enfoque mas estructurado que intenta mejorar o guiar esa produccion hacia la sostenibilidad ambiental, social y economica."
        )

    def _build_topic_line(self, insights: list[dict], keywords: set[str]) -> str:
        return ""

    def _style_config(self, response_style: str) -> dict:
        return RESPONSE_STYLE_GUIDANCE.get(response_style, RESPONSE_STYLE_GUIDANCE["academico"])

    def _format_insight_summary(self, summary: str, response_style: str) -> str:
        cleaned = self._clean_sentence(summary)

        if response_style == "simple":
            cleaned = re.sub(r"^Los documentos indican que\s+", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"^La evidencia sugiere que\s+", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"^Se identifica que\s+", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\bademas\b", "tambien", cleaned, flags=re.IGNORECASE)
            if cleaned:
                cleaned = cleaned[:1].upper() + cleaned[1:]
            return self._ensure_sentence(cleaned)

        if response_style == "tecnico":
            cleaned = re.sub(r"^Los documentos indican que\s+", "", cleaned, flags=re.IGNORECASE)
            if not re.match(r"^(Se identifica|Se observa|Se registra|El manejo|La produccion|La dinamica|El proceso)", cleaned):
                cleaned = f"Se observa que {self._lowercase_first(cleaned)}"
            return self._ensure_sentence(cleaned)

        cleaned = re.sub(r"^Los documentos indican que\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^La evidencia sugiere que\s+", "", cleaned, flags=re.IGNORECASE)
        if not re.match(r"^(Se observa|Se identifica|En la practica|En Tungurahua|La produccion|El cultivo|La actividad)", cleaned):
            cleaned = cleaned[:1].upper() + cleaned[1:]
        return self._ensure_sentence(cleaned)

    def _humanize_extractive_summary(self, summary: str, response_style: str) -> str:
        cleaned = self._clean_sentence(summary)
        cleaned = re.sub(r"^[A-ZÁÉÍÓÚÜÑ0-9\s]{18,}\s+", "", cleaned)
        cleaned = re.sub(r"^\d+[.)]?\s*", "", cleaned)
        cleaned = re.sub(r"\bRecreando y mejorando la agricultura tradicional\s*\d*[.)]?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bAdemas,\s*", "Tambien, ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bsegun\s+los\s+documentos?,?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bRACIONALIDAD ECOLOGICA DE LOS AGROECOSISTEMAS TRADICIONALES\b", "", cleaned)
        cleaned = re.sub(r"\ba\s+lo\s+largo\s+de\s+siglos\s+de\.?\s*", "a lo largo del tiempo ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bTambien,\s*importancia\s+crucial\b", "Esto tambien es importante", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -,:;.")

        if not cleaned:
            return "Hay informacion relacionada, pero el fragmento recuperado no es suficientemente claro para citarlo directamente."

        if response_style == "simple":
            cleaned = cleaned.replace("Tambien,", "Tambien")
        if cleaned:
            cleaned = cleaned[:1].upper() + cleaned[1:]
        return self._ensure_sentence(cleaned)

    def _select_summary_chunks(self, chunks: list[dict]) -> list[dict]:
        sorted_chunks = sorted(
            chunks,
            key=lambda chunk: (len(chunk["tokens"]), len(chunk["text"])),
            reverse=True,
        )
        selected = []
        seen_pages = set()
        for chunk in sorted_chunks:
            page_label = chunk.get("page_label", "")
            if page_label and page_label in seen_pages:
                continue
            selected.append(chunk)
            if page_label:
                seen_pages.add(page_label)
            if len(selected) >= 6:
                break

        return selected or sorted_chunks[:6]

    def _source_reference(self, file_name: str, page_label: str, score: float) -> str:
        display_title = self._display_title(file_name)
        if page_label:
            return f"{display_title}, pagina {page_label}, relevancia {score}"
        return f"{display_title}, relevancia {score}"

    def _build_conclusion(
        self,
        question: str,
        insights: list[dict],
        keywords: set[str],
        response_style: str,
    ) -> str:
        if not insights:
            return ""

        top_summary = insights[0]["summary"]
        styled_top_summary = self._format_insight_summary(top_summary, response_style)

        if response_style == "simple":
            return styled_top_summary

        if response_style == "tecnico":
            return styled_top_summary

        return styled_top_summary

    def _collect_topics(self, insights: list[dict], keywords: set[str]) -> list[str]:
        frequencies: dict[str, int] = {}
        for insight in insights:
            for token in insight["keywords"]:
                if token in keywords or token in GENERIC_TOPIC_WORDS or len(token) < 4:
                    continue
                frequencies[token] = frequencies.get(token, 0) + 1

        ranked = sorted(frequencies.items(), key=lambda item: (item[1], item[0]), reverse=True)
        return [token for token, _ in ranked[:6]]

    def _fallback_snippet(self, text: str) -> str:
        cleaned = self._clean_sentence(self._clean_ocr_text(text[:260]))
        if not cleaned:
            return ""
        return self._ensure_sentence(cleaned)

    def _clean_ocr_text(self, text: str) -> str:
        cleaned = self._repair_mojibake(str(text or ""))
        cleaned = unicodedata.normalize("NFKC", cleaned)
        cleaned = cleaned.replace("\u00ad", "")
        cleaned = cleaned.replace("\uf0b7", "- ")
        cleaned = cleaned.replace("\u2022", "- ")
        cleaned = re.sub(r"(?<=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])-\s+(?=[a-záéíóúüñ])", "", cleaned)
        cleaned = re.sub(r"\b[a-záéíóúüñ]{2,6}-\s*\d{1,4}\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"(?<=[.!?;:])\s*\d{1,4}\s+(?=[A-ZÁÉÍÓÚÜÑ])", " ", cleaned)
        cleaned = re.sub(r"\s+\d{1,4}\s*$", "", cleaned)
        cleaned = re.sub(r"[\"“”']\s*[\"“”']", "", cleaned)
        cleaned = re.sub(r"[ \t]+([,.;:!?])", r"\1", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        return cleaned.strip()

    def _clean_generated_answer(self, text: str) -> str:
        cleaned = self._clean_ocr_text(text)
        cleaned = re.sub(r"\s+\d{1,4}(?=\s*(?:\n|$))", "", cleaned)
        cleaned = re.sub(r"\b[a-záéíóúüñ]{2,6}-\s*(?=[,.!?;:]|$)", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _clean_sentence(self, text: str) -> str:
        cleaned = " ".join(self._clean_ocr_text(text).strip().split())
        cleaned = re.sub(r"\[[^\]]+\]", "", cleaned)
        cleaned = re.sub(r"\(\s*\)", "", cleaned)
        return cleaned.strip()

    def _ensure_sentence(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            return ""
        if cleaned[-1] not in ".!?":
            return f"{cleaned}."
        return cleaned

    def _lowercase_first(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            return ""
        return cleaned[:1].lower() + cleaned[1:]

    def _question_style(self, question: str) -> str:
        normalized = self._normalize_text(question)
        if normalized.startswith("como"):
            return "como"
        if normalized.startswith("por que") or normalized.startswith("porque"):
            return "por_que"
        if normalized.startswith("cuales") or normalized.startswith("cual"):
            return "cuales"
        return "general"

    def _extract_keywords(self, question: str) -> set[str]:
        return self._normalize_tokens(question)

    def _normalize_tokens(self, text: str) -> set[str]:
        normalized_text = self._normalize_text(text)
        tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", normalized_text)
            if len(token) > 2 and token not in STOP_WORDS
        }
        return tokens

    def _normalize_text(self, text: str) -> str:
        ascii_text = unicodedata.normalize("NFKD", text.lower())
        return "".join(char for char in ascii_text if not unicodedata.combining(char))
