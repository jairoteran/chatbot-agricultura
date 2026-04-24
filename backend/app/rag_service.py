from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SentenceSplitter

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 5
SIMILARITY_THRESHOLD = 0.35
REQUIRED_STORAGE_FILES = (
    "docstore.json",
    "index_store.json",
    "vector_store.json",
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


class RAGService:
    def __init__(self) -> None:
        self.index: VectorStoreIndex | None = None
        self.retriever = None
        self.indexed_files: list[str] = []
        self.chunk_cache: list[dict] = []
        self._configure_embeddings()
        self.ensure_index_ready()

    def _configure_embeddings(self) -> None:
        try:
            Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
        except Exception as exc:
            raise RuntimeError(
                "No fue posible cargar el modelo de embeddings. "
                "Si es la primera ejecucion, verifica tu conexion a internet para descargar el modelo "
                f"'{EMBED_MODEL}'. Detalle original: {exc}"
            ) from exc

    def ensure_index_ready(self, force_rebuild: bool = False) -> None:
        self.index = self._load_or_build_index(force_rebuild=force_rebuild)
        self.retriever = self.index.as_retriever(similarity_top_k=TOP_K)

    def _load_or_build_index(self, force_rebuild: bool = False) -> VectorStoreIndex:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        documents = self._load_documents()
        current_manifest = self._build_manifest(documents)
        self.indexed_files = [item["file_name"] for item in current_manifest["files"]]

        if not documents:
            raise RuntimeError(
                "No se encontraron archivos PDF en backend/data. "
                "Agrega al menos un documento antes de iniciar el servicio."
            )

        if not force_rebuild and self._has_usable_persisted_index(current_manifest):
            storage_context = StorageContext.from_defaults(persist_dir=str(STORAGE_DIR))
            self.chunk_cache = json.loads(CHUNK_CACHE_FILE.read_text(encoding="utf-8"))
            return load_index_from_storage(storage_context)

        splitter = SentenceSplitter(chunk_size=700, chunk_overlap=120)
        nodes = splitter.get_nodes_from_documents(documents)
        self.chunk_cache = self._serialize_nodes(nodes)
        index = VectorStoreIndex(nodes)
        index.storage_context.persist(persist_dir=str(STORAGE_DIR))
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
        return SimpleDirectoryReader(
            input_dir=str(DATA_DIR),
            required_exts=[".pdf"],
            recursive=True,
            filename_as_id=True,
        ).load_data()

    def _has_usable_persisted_index(self, current_manifest: dict) -> bool:
        has_required_files = all((STORAGE_DIR / file_name).exists() for file_name in REQUIRED_STORAGE_FILES)
        if not has_required_files or not MANIFEST_FILE.exists() or not CHUNK_CACHE_FILE.exists():
            return False

        try:
            stored_manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False

        return stored_manifest == current_manifest

    def _build_manifest(self, documents: list) -> dict:
        files_by_path: dict[str, dict] = {}

        for document in documents:
            path = Path(document.metadata.get("file_path", ""))
            if not path.exists():
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

    def get_status(self) -> dict:
        return {
            "status": "ok",
            "detail": "Servicio listo",
            "indexed_files": self.indexed_files,
            "indexed_file_count": len(self.indexed_files),
            "index_ready": self.index is not None,
        }

    def reindex(self) -> dict:
        self.ensure_index_ready(force_rebuild=True)
        return {
            "status": "ok",
            "detail": "Indice reconstruido correctamente",
            "indexed_files": self.indexed_files,
        }

    def query(self, question: str) -> dict:
        if self.retriever is None:
            raise RuntimeError("El indice aun no esta listo.")

        keywords = self._extract_keywords(question)
        vector_candidates = self._vector_candidates(question, keywords)
        lexical_candidates = self._lexical_candidates(keywords)
        merged_candidates = self._merge_candidates(vector_candidates, lexical_candidates)

        filtered_nodes = [
            item for item in merged_candidates if item["keyword_overlap"] > 0
        ] or merged_candidates[:3]

        if not filtered_nodes:
            return {
                "answer": (
                    "No se encontro informacion suficiente en los documentos cargados "
                    "para responder esa pregunta."
                ),
                "found": False,
                "sources": [],
            }

        source_chunks = []
        evidence_blocks = []

        for item in filtered_nodes[:4]:
            file_name = item["file_name"]
            normalized_text = item["text"]
            excerpt = normalized_text[:650]
            score = item["score"]

            source_chunks.append(
                {
                    "file_name": file_name,
                    "score": score,
                    "text": excerpt,
                }
            )
            evidence_blocks.append((file_name, score, normalized_text))

        if not any(item["keyword_overlap"] > 0 for item in filtered_nodes):
            return {
                "answer": (
                    "No se encontro informacion suficientemente relacionada con la pregunta "
                    "dentro de los documentos cargados."
                ),
                "found": False,
                "sources": [],
            }

        answer = self._compose_answer(question, evidence_blocks)

        return {
            "answer": answer,
            "found": True,
            "sources": source_chunks,
        }

    def _vector_candidates(self, question: str, keywords: set[str]) -> list[dict]:
        ranked_nodes = []

        for node in self.retriever.retrieve(question):
            if node.score is None or float(node.score) < SIMILARITY_THRESHOLD:
                continue

            normalized_text = " ".join(node.text.strip().split())
            ranked_nodes.append(
                {
                    "file_name": self._node_file_name(node.metadata or {}),
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
            key = (candidate["file_name"], candidate["text"][:220])
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
                    "text": text,
                    "tokens": sorted(self._normalize_tokens(text)),
                }
            )

        return serialized

    def _node_file_name(self, metadata: dict) -> str:
        return metadata.get("file_name") or metadata.get("filename") or "Documento"

    def _compose_answer(self, question: str, evidence_blocks: list[tuple[str, float, str]]) -> str:
        keywords = self._extract_keywords(question)
        selected_sentences: list[str] = []

        for file_name, score, text in evidence_blocks:
            best_sentences = self._best_sentences_for_question(text, keywords)
            for sentence in best_sentences[:2]:
                candidate = f"- {sentence} [{file_name}, relevancia {score}]"
                if candidate not in selected_sentences:
                    selected_sentences.append(candidate)
            if len(selected_sentences) >= 4:
                break

        if not selected_sentences:
            for file_name, score, text in evidence_blocks[:3]:
                fallback_excerpt = text[:260].strip()
                selected_sentences.append(
                    f"- {fallback_excerpt} [{file_name}, relevancia {score}]"
                )

        intro = (
            "Encontre informacion relevante en los documentos cargados. "
            "Con base unicamente en esos textos, esto es lo que pude identificar:"
        )
        closing = (
            "\n\nSi necesitas mas precision, prueba con una pregunta mas especifica "
            "sobre una seccion, dato o documento concreto."
        )
        return f"{intro}\n\n" + "\n".join(selected_sentences) + closing

    def _best_sentences_for_question(self, text: str, keywords: set[str]) -> list[str]:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
            if len(sentence.strip()) >= 40
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

    def _extract_keywords(self, question: str) -> set[str]:
        return self._normalize_tokens(question)

    def _normalize_tokens(self, text: str) -> set[str]:
        tokens = {
            token
            for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
            if len(token) > 2 and token not in STOP_WORDS
        }
        return tokens
