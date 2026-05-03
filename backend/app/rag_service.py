from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from hashlib import sha256
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TOP_K = 5
SIMILARITY_THRESHOLD = 0.35
REQUIRED_STORAGE_FILES = (
    "docstore.json",
    "index_store.json",
    "default__vector_store.json",
)
MANIFEST_FILE = STORAGE_DIR / "manifest.json"
CHUNK_CACHE_FILE = STORAGE_DIR / "chunk_cache.json"
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
            "Usa un tono academico claro y ordenado. Prioriza precision, sintesis y redaccion apta para tesis o trabajos formales."
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
            "Usa un tono sencillo y cercano. Explica con palabras faciles, evita tecnicismos innecesarios y busca que cualquier persona lo entienda."
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
            "Usa un tono tecnico y preciso. Conserva la terminologia relevante del dominio y enfatiza procedimientos, criterios y relaciones causales."
        ),
    },
}


def _detect_deployment_mode() -> str:
    if os.getenv("VERCEL") == "1":
        return "vercel"
    if os.getenv("RENDER") == "true":
        return "render"
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return "railway"
    if os.getenv("FLY_APP_NAME"):
        return "fly"
    return "local"


class RAGService:
    def __init__(self, progress_callback=None) -> None:
        self.progress_callback = progress_callback
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
        self.deployment_mode = _detect_deployment_mode()
        raw_allow_reindex = os.getenv("ALLOW_RUNTIME_REINDEX", "").strip().lower()
        self.allow_reindex = raw_allow_reindex in {"1", "true", "yes"}
        if not raw_allow_reindex and self.deployment_mode in {"local", "render"}:
            self.allow_reindex = True
        self.gemini_client = None
        self.openai_client = None
        self.vector_backend_ready = False
        self.embed_model_name = ""
        self._current_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        self.last_interaction_label = "Sin consultas"
        self.last_response_ms = 0
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.last_total_tokens = 0
        self._report_progress(5, "starting", "Preparando configuracion del servicio...")
        self._configure_llm_client()
        self._report_progress(18, "embedding-setup", "Configurando el backend de embeddings...")
        self._configure_embeddings()
        self._report_progress(32, "index-check", "Verificando el indice documental...")
        self.ensure_index_ready()
        self._report_progress(100, "ready", "Servicio listo")

    def _report_progress(self, progress: int, stage: str, detail: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(progress, stage, detail)

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

    def _configure_embeddings(self) -> None:
        if not self._should_prepare_vector_backend():
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
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._report_progress(42, "manifest-scan", "Analizando documentos y archivos del indice...")
        current_manifest = self._build_manifest()
        self.indexed_files = [item["file_name"] for item in current_manifest["files"]]

        if (
            not force_rebuild
            and self._can_boot_from_chunk_cache_only()
            and self._read_manifest() == current_manifest
        ):
            self._report_progress(72, "chunk-cache", "Cargando indice desde chunk cache...")
            self.chunk_cache = self._read_chunk_cache()
            self.index_stale = False
            self.index_detail = "Servicio listo"
            self.last_index_source = "chunk-cache"
            return None

        if not current_manifest["files"]:
            if self._has_chunk_cache():
                self._report_progress(72, "chunk-cache", "Cargando indice previamente almacenado...")
                self.chunk_cache = self._read_chunk_cache()
                self.last_index_source = "chunk-cache"
                if not self.indexed_files:
                    stored_manifest = self._read_manifest()
                    self.indexed_files = [item["file_name"] for item in stored_manifest.get("files", [])]
                self.index_stale = False
                self.index_detail = "Servicio listo"
                return None

            raise RuntimeError(
                "No se encontraron archivos PDF en backend/data ni un chunk_cache utilizable en backend/storage."
            )

        if not force_rebuild and self._has_usable_persisted_index(current_manifest):
            from llama_index.core import StorageContext, load_index_from_storage

            self._report_progress(78, "storage-index", "Cargando indice persistido...")
            storage_context = StorageContext.from_defaults(persist_dir=str(STORAGE_DIR))
            self.chunk_cache = self._read_chunk_cache()
            self.index_stale = False
            self.index_detail = "Servicio listo"
            self.last_index_source = "storage"
            return load_index_from_storage(storage_context)

        if self.deployment_mode != "local" and not self.allow_reindex:
            if self._has_chunk_cache():
                self.chunk_cache = self._read_chunk_cache()
                self.index_stale = True
                self.index_detail = (
                    "Se detectaron cambios en backend/data, pero este despliegue no puede reindexar en vivo. "
                    "Reconstruye backend/storage localmente y vuelve a desplegar."
                )
                self.last_index_source = "chunk-cache"
                return None

            raise RuntimeError(
                "No se encontro un indice persistido utilizable para este despliegue. "
                "En Vercel debes incluir backend/storage actualizado en el repositorio o habilitar ALLOW_RUNTIME_REINDEX."
            )

        if not self.vector_backend_ready:
            raise RuntimeError(
                "No fue posible cargar el backend de embeddings necesario para reconstruir el indice."
            )

        self._report_progress(55, "document-load", "Leyendo documentos PDF para reconstruir el indice...")
        documents = self._load_documents()
        from llama_index.core import VectorStoreIndex
        from llama_index.core.node_parser import SentenceSplitter

        self._report_progress(68, "node-build", "Dividiendo documentos en fragmentos analizables...")
        splitter = SentenceSplitter(chunk_size=700, chunk_overlap=120)
        nodes = splitter.get_nodes_from_documents(documents)
        self._report_progress(82, "vector-index", "Construyendo el indice vectorial...")
        self.chunk_cache = self._serialize_nodes(nodes)
        index = VectorStoreIndex(nodes)
        self._report_progress(92, "persist-index", "Guardando el indice para futuros arranques...")
        index.storage_context.persist(persist_dir=str(STORAGE_DIR))
        self.index_stale = False
        self.index_detail = "Servicio listo"
        self.last_index_source = "rebuild"
        MANIFEST_FILE.write_text(
            json.dumps(current_manifest, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        CHUNK_CACHE_FILE.write_text(
            json.dumps(self.chunk_cache, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        return index

    def _load_documents(self) -> list:
        from llama_index.core import SimpleDirectoryReader

        return SimpleDirectoryReader(
            input_dir=str(DATA_DIR),
            required_exts=[".pdf"],
            recursive=True,
            filename_as_id=True,
        ).load_data()

    def _has_chunk_cache(self) -> bool:
        return MANIFEST_FILE.exists() and CHUNK_CACHE_FILE.exists()

    def _should_prepare_vector_backend(self) -> bool:
        return self.deployment_mode == "local" or self.allow_reindex

    def _can_boot_from_chunk_cache_only(self) -> bool:
        return self._has_chunk_cache() and not self._should_prepare_vector_backend()

    def _read_manifest(self) -> dict:
        if not MANIFEST_FILE.exists():
            return {"embed_model": self.embed_model_name, "files": []}
        try:
            return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"embed_model": self.embed_model_name, "files": []}

    def _read_chunk_cache(self) -> list[dict]:
        try:
            return json.loads(CHUNK_CACHE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("No fue posible leer backend/storage/chunk_cache.json.") from exc

    def _has_usable_persisted_index(self, current_manifest: dict) -> bool:
        if not self.vector_backend_ready:
            return False

        has_required_files = all((STORAGE_DIR / file_name).exists() for file_name in REQUIRED_STORAGE_FILES)
        if not has_required_files or not MANIFEST_FILE.exists() or not CHUNK_CACHE_FILE.exists():
            return False

        stored_manifest = self._read_manifest()

        return stored_manifest == current_manifest

    def _build_manifest(self) -> dict:
        files_by_path: dict[str, dict] = {}

        for path in DATA_DIR.rglob("*.pdf"):
            if not path.is_file():
                continue

            stat = path.stat()
            file_hash = sha256(
                f"{path.resolve()}::{stat.st_mtime_ns}::{stat.st_size}".encode("utf-8")
            ).hexdigest()
            relative_path = str(path.relative_to(DATA_DIR)).replace("\\", "/")
            files_by_path[relative_path] = {
                "file_name": path.name,
                "relative_path": relative_path,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "fingerprint": file_hash,
            }

        files = sorted(files_by_path.values(), key=lambda item: item["relative_path"])
        return {
            "embed_model": EMBED_MODEL,
            "files": files,
        }

    def _refresh_index_if_needed(self) -> None:
        current_manifest = self._build_manifest()
        stored_manifest = self._read_manifest()
        has_changes = stored_manifest != current_manifest

        self.indexed_files = [item["file_name"] for item in current_manifest["files"]]

        if not has_changes:
            self.index_stale = False
            self.index_detail = "Servicio listo"
            return

        if self.allow_reindex and self.vector_backend_ready:
            self.ensure_index_ready(force_rebuild=True)
            self.index_detail = "Se detectaron PDFs nuevos o actualizados y el indice se reconstruyo."
            return

        self.index_stale = True
        self.index_detail = (
            "Se detectaron PDFs nuevos o actualizados, pero el indice actual no los incluye. "
            "Reconstruye backend/storage o habilita el reindexado en vivo."
        )

    def get_status(self) -> dict:
        self._refresh_index_if_needed()
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
            "last_interaction_label": self.last_interaction_label,
            "last_response_ms": self.last_response_ms,
            "last_input_tokens": self.last_input_tokens,
            "last_output_tokens": self.last_output_tokens,
            "last_total_tokens": self.last_total_tokens,
        }

    def reindex(self) -> dict:
        if not self.allow_reindex:
            raise RuntimeError(
                "La reindexacion en tiempo de ejecucion esta deshabilitada en este despliegue. "
                "Reconstruye el indice antes de desplegar o habilita ALLOW_RUNTIME_REINDEX."
            )

        self.ensure_index_ready(force_rebuild=True)
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

        small_talk_answer = self._small_talk_answer(question)
        if small_talk_answer:
            result = {
                "answer": small_talk_answer,
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
        ] or merged_candidates[:3]

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

        for item in filtered_nodes[:4]:
            file_name = item["file_name"]
            page_label = item.get("page_label", "")
            normalized_text = item["text"]
            excerpt = normalized_text[:650]
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
                "text": chunk["text"][:650],
            }
            for chunk in selected_chunks[:4]
        ]
        evidence_blocks = [
            (
                chunk["file_name"],
                chunk.get("page_label", ""),
                1.0,
                chunk["text"],
            )
            for chunk in selected_chunks[:5]
        ]

        style_config = self._style_config(response_style)
        prompt = (
            f"Resume el documento '{selected_chunks[0]['file_name']}' de forma organizada.\n"
            "Debes escribir en espanol, sin copiar el texto literalmente.\n"
            f"{style_config['summary_instruction']}\n"
            "Organiza la respuesta con estas secciones cuando aporten claridad: **Resumen**, **Ideas clave**, **Conclusion**.\n"
            "Usa listas con guiones para las ideas clave.\n"
            "Si puedes, menciona de forma breve las paginas mas utiles al final bajo **Referencias**.\n"
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
        return candidates[:8]

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
        return ranked[:8]

    def _serialize_nodes(self, nodes: list) -> list[dict]:
        serialized = []

        for node in nodes:
            metadata = node.metadata or {}
            text = " ".join(node.text.strip().split())
            if not text:
                continue

            serialized.append(
                {
                    "file_name": self._node_file_name(metadata),
                    "page_label": self._node_page_label(metadata),
                    "text": text,
                    "tokens": sorted(self._normalize_tokens(text)),
                }
            )

        return serialized

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
                fallback_points.append(f"- {snippet} [{self._source_reference(file_name, page_label, score)}]")

            if not fallback_points:
                return (
                    "Encontre fragmentos relacionados, pero no suficiente contexto para elaborar "
                    "una respuesta clara sin arriesgar una interpretacion incorrecta."
                )

            return (
                f"{style_config['sections'][0]} Encontre informacion relacionada, pero el contenido recuperado es parcial.\n\n"
                f"{style_config['fallback_points_label']}\n"
                + "\n".join(fallback_points)
                + f"\n\n{style_config['sections'][3]} Si quieres, puedo afinar la busqueda con una pregunta mas especifica."
            )

        overview = self._build_overview(question, insights, keywords, response_style)
        topic_line = self._build_topic_line(insights, keywords)
        conclusion = self._build_conclusion(question, insights, keywords, response_style)
        answer_lines = [style_config["sections"][0], overview, "", style_config["sections"][1]]

        for insight in insights[:3]:
            answer_lines.append(
                f"- {self._format_insight_summary(insight['summary'], response_style)} "
                f"[{self._source_reference(insight['file_name'], insight['page_label'], insight['score'])}]"
            )

        if topic_line:
            answer_lines.extend(["", f"{style_config['related_label']} {topic_line}"])

        if conclusion:
            answer_lines.extend(["", f"{style_config['sections'][2]} {conclusion}"])

        answer_lines.extend(
            [
                "",
                f"{style_config['sections'][3]} La respuesta esta sintetizada a partir de los fragmentos recuperados, no copiada de forma literal.",
            ]
        )
        return "\n".join(answer_lines)

    def _generate_llm_answer(
        self,
        question: str,
        evidence_blocks: list[tuple[str, str, float, str]],
        history: list[dict],
        response_style: str = "academico",
    ) -> str:
        style_config = self._style_config(response_style)
        evidence_text = self._format_evidence_for_llm(evidence_blocks)
        conversation_text = self._format_history_for_llm(history)
        prompt = (
            "Responde en espanol como un asistente conversacional que analiza documentos.\n"
            "Tu tarea es razonar sobre la evidencia recuperada y explicarla con claridad.\n"
            "No copies frases largas del contexto. Sintetiza, conecta ideas y responde como un verdadero chatbot.\n"
            "Debes usar solo la evidencia proporcionada. Si la evidencia no alcanza, dilo claramente.\n"
            "No inventes datos ni cites paginas inexistentes.\n"
            "Prefiere una respuesta natural y organizada.\n"
            f"{style_config['llm_instruction']}\n"
            "\n"
            "Historial reciente:\n"
            f"{conversation_text}\n\n"
            "Pregunta actual:\n"
            f"{question}\n\n"
            "Evidencia recuperada:\n"
            f"{evidence_text}\n\n"
            "Instrucciones de salida:\n"
            "1. Responde de forma clara y directa.\n"
            "2. Explica el sentido de la informacion, no la repitas literalmente.\n"
            f"3. Organiza la respuesta con estas secciones cuando aporten claridad: {style_config['sections'][0]}, {style_config['sections'][1]}, {style_config['sections'][2]}.\n"
            "4. Usa listas con guiones si enumeras ideas y adapta el nivel de detalle al estilo solicitado.\n"
            f"5. Si notas limites o ambiguedades en la evidencia, mencionalos al final en una frase breve bajo {style_config['sections'][3]}.\n"
            f"6. Si mencionas temas complementarios, presentalos bajo {style_config['related_label']}.\n"
        )

        try:
            if self.gemini_client is not None:
                response = self.gemini_client.models.generate_content(
                    model=self.llm_model,
                    contents=prompt,
                )
                self._capture_usage(response)
                output_text = getattr(response, "text", "") or ""
                return output_text.strip()

            response = self.openai_client.responses.create(model=self.llm_model, input=prompt)
            self._capture_usage(response)
        except Exception:
            return ""

        output_text = getattr(response, "output_text", "") or ""
        return output_text.strip()

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
        for index, (file_name, page_label, score, text) in enumerate(evidence_blocks[:4], start=1):
            blocks.append(
                f"[Fuente {index}] Documento: {self._display_title(file_name)} | pagina: {page_label or 'sin pagina'} | relevancia: {score}\n{text[:1400]}"
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
        return f"Los documentos indican que {fragment}."

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
        primary_topics = self._collect_topics(insights, keywords)
        topic_text = ", ".join(primary_topics[:3])

        if response_style == "simple":
            if question_style == "como":
                base = "Segun los fragmentos mas utiles, asi se entiende o se aplica el tema que preguntaste"
            elif question_style == "por_que":
                base = "Los textos ayudan a entender por que ocurre o por que se recomienda ese tema"
            elif question_style == "cuales":
                base = "Los documentos muestran varios puntos concretos relacionados con tu pregunta"
            else:
                base = "Con lo que aparece en los documentos, esto es lo mas importante para responderte"
        elif response_style == "tecnico":
            if question_style == "como":
                base = "La evidencia recuperada describe el procedimiento o la aplicacion operativa del tema consultado"
            elif question_style == "por_que":
                base = "La evidencia disponible permite identificar los factores o fundamentos tecnicos asociados al tema consultado"
            elif question_style == "cuales":
                base = "Los fragmentos recuperados permiten discriminar componentes, criterios o elementos tecnicos vinculados con la consulta"
            else:
                base = "La respuesta puede sintetizarse a partir de la evidencia recuperada con enfoque tecnico"
        elif question_style == "como":
            base = "Al revisar los fragmentos mas relevantes, se describe principalmente como ocurre o se aplica el tema consultado"
        elif question_style == "por_que":
            base = "Los textos recuperados apuntan sobre todo a las causas o razones asociadas al tema consultado"
        elif question_style == "cuales":
            base = "Los documentos permiten identificar varios elementos concretos relacionados con tu pregunta"
        else:
            base = "A partir de los fragmentos recuperados, se puede responder de forma sintetizada"

        if topic_text:
            return f"{base}. Los temas que mas sostienen la respuesta son {topic_text}."
        return f"{base}."

    def _build_topic_line(self, insights: list[dict], keywords: set[str]) -> str:
        topics = self._collect_topics(insights, keywords)
        if not topics:
            return ""
        return ", ".join(topics[:5]) + "."

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
            if not re.match(r"^(Se identifica|Se observa|Se registra|El manejo|La evidencia)", cleaned):
                cleaned = f"Se identifica que {self._lowercase_first(cleaned)}"
            return self._ensure_sentence(cleaned)

        if not re.match(r"^(La evidencia|Los documentos|Se observa|Se identifica)", cleaned):
            cleaned = f"La evidencia sugiere que {self._lowercase_first(cleaned)}"
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

        dominant_topics = self._collect_topics(insights, keywords)
        top_summary = insights[0]["summary"]
        styled_top_summary = self._format_insight_summary(top_summary, response_style)

        if response_style == "simple":
            if dominant_topics:
                return (
                    f"En pocas palabras, para entender este tema conviene fijarse sobre todo en {', '.join(dominant_topics[:3])}. "
                    f"{styled_top_summary}"
                )
            return styled_top_summary

        if response_style == "tecnico":
            if dominant_topics:
                return (
                    f"En terminos tecnicos, la interpretacion del tema depende principalmente de {', '.join(dominant_topics[:3])}. "
                    f"{styled_top_summary}"
                )
            return styled_top_summary

        if dominant_topics:
            return (
                f"En conjunto, la evidencia sugiere que el tema se entiende mejor si se consideran especialmente {', '.join(dominant_topics[:3])}, "
                f"y que {self._lowercase_first(styled_top_summary)}"
            )
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
        cleaned = self._clean_sentence(text[:260])
        if not cleaned:
            return ""
        return self._ensure_sentence(cleaned)

    def _clean_sentence(self, text: str) -> str:
        cleaned = " ".join(text.strip().split())
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
