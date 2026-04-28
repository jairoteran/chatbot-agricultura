from __future__ import annotations

import json
import os
import re
import time
import unicodedata
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
from google import genai
from openai import OpenAI

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


class RAGService:
    def __init__(self) -> None:
        self.index: VectorStoreIndex | None = None
        self.retriever = None
        self.indexed_files: list[str] = []
        self.chunk_cache: list[dict] = []
        self.last_index_source = "startup"
        self.last_index_seconds = 0.0
        self.response_mode = "extractive"
        self.llm_provider = ""
        self.llm_model = ""
        self.gemini_client = None
        self.openai_client = None
        self._configure_llm_client()
        self._configure_embeddings()
        self.ensure_index_ready()

    def _configure_llm_client(self) -> None:
        gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if gemini_api_key:
            self.gemini_client = genai.Client(api_key=gemini_api_key)
            self.response_mode = "generative-rag"
            self.llm_provider = "gemini"
            self.llm_model = GEMINI_MODEL
            return

        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
            self.response_mode = "generative-rag"
            self.llm_provider = "openai"
            self.llm_model = OPENAI_MODEL

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
        started_at = time.perf_counter()
        self.index = self._load_or_build_index(force_rebuild=force_rebuild)
        self.retriever = self.index.as_retriever(similarity_top_k=TOP_K)
        self.last_index_seconds = round(time.perf_counter() - started_at, 2)

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
            self.last_index_source = "storage"
            return load_index_from_storage(storage_context)

        splitter = SentenceSplitter(chunk_size=700, chunk_overlap=120)
        nodes = splitter.get_nodes_from_documents(documents)
        self.chunk_cache = self._serialize_nodes(nodes)
        index = VectorStoreIndex(nodes)
        index.storage_context.persist(persist_dir=str(STORAGE_DIR))
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
            "index_source": self.last_index_source,
            "last_index_seconds": self.last_index_seconds,
            "embed_model": EMBED_MODEL,
            "response_mode": self.response_mode,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
        }

    def reindex(self) -> dict:
        self.ensure_index_ready(force_rebuild=True)
        return {
            "status": "ok",
            "detail": "Indice reconstruido correctamente",
            "indexed_files": self.indexed_files,
            "index_source": self.last_index_source,
            "last_index_seconds": self.last_index_seconds,
        }

    def query(self, question: str, history: list[dict] | None = None) -> dict:
        if self.retriever is None:
            raise RuntimeError("El indice aun no esta listo.")

        small_talk_answer = self._small_talk_answer(question)
        if small_talk_answer:
            return {
                "answer": small_talk_answer,
                "found": True,
                "sources": [],
            }

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

        answer = self._compose_answer(question, evidence_blocks, history or [])

        return {
            "answer": answer,
            "found": True,
            "sources": source_chunks,
        }

    def _small_talk_answer(self, question: str) -> str:
        normalized_question = " ".join(question.strip().split())
        for pattern, answer in SMALL_TALK_PATTERNS:
            if pattern.match(normalized_question):
                return answer
        return ""

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

    def _compose_answer(
        self,
        question: str,
        evidence_blocks: list[tuple[str, float, str]],
        history: list[dict],
    ) -> str:
        if self.gemini_client is not None or self.openai_client is not None:
            generated_answer = self._generate_llm_answer(question, evidence_blocks, history)
            if generated_answer:
                return generated_answer

        keywords = self._extract_keywords(question)
        insights = self._build_analysis_insights(evidence_blocks, keywords)

        if not insights:
            fallback_points = []
            for file_name, score, text in evidence_blocks[:3]:
                snippet = self._fallback_snippet(text)
                if not snippet:
                    continue
                fallback_points.append(f"- {snippet} [{file_name}, relevancia {score}]")

            if not fallback_points:
                return (
                    "Encontre fragmentos relacionados, pero no suficiente contexto para elaborar "
                    "una respuesta clara sin arriesgar una interpretacion incorrecta."
                )

            return (
                "**Respuesta breve:** Encontre informacion relacionada, pero el contenido recuperado es parcial.\n\n"
                "**Puntos rescatables:**\n"
                + "\n".join(fallback_points)
                + "\n\n**Observacion:** Si quieres, puedo afinar la busqueda con una pregunta mas especifica."
            )

        overview = self._build_overview(question, insights, keywords)
        topic_line = self._build_topic_line(insights, keywords)
        conclusion = self._build_conclusion(question, insights, keywords)
        answer_lines = ["**Respuesta breve:**", overview, "", "**Puntos clave:**"]

        for insight in insights[:3]:
            answer_lines.append(
                f"- {insight['summary']} [{insight['file_name']}, relevancia {insight['score']}]"
            )

        if topic_line:
            answer_lines.extend(["", f"**Temas relacionados:** {topic_line}"])

        if conclusion:
            answer_lines.extend(["", f"**Conclusion:** {conclusion}"])

        answer_lines.extend(
            [
                "",
                "**Nota:** La respuesta esta sintetizada a partir de los fragmentos recuperados, no copiada de forma literal.",
            ]
        )
        return "\n".join(answer_lines)

    def _generate_llm_answer(
        self,
        question: str,
        evidence_blocks: list[tuple[str, float, str]],
        history: list[dict],
    ) -> str:
        evidence_text = self._format_evidence_for_llm(evidence_blocks)
        conversation_text = self._format_history_for_llm(history)
        prompt = (
            "Responde en espanol como un asistente conversacional que analiza documentos.\n"
            "Tu tarea es razonar sobre la evidencia recuperada y explicarla con claridad.\n"
            "No copies frases largas del contexto. Sintetiza, conecta ideas y responde como un verdadero chatbot.\n"
            "Debes usar solo la evidencia proporcionada. Si la evidencia no alcanza, dilo claramente.\n"
            "No inventes datos ni cites paginas inexistentes.\n"
            "Prefiere una respuesta natural y organizada.\n"
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
            "3. Organiza la respuesta con estas secciones cuando aporten claridad: **Respuesta breve**, **Puntos clave**, **Conclusion**.\n"
            "4. Usa listas con guiones si enumeras ideas.\n"
            "5. Si notas limites o ambiguedades en la evidencia, mencialos al final en una frase breve bajo **Nota**.\n"
        )

        try:
            if self.gemini_client is not None:
                response = self.gemini_client.models.generate_content(
                    model=self.llm_model,
                    contents=prompt,
                )
                output_text = getattr(response, "text", "") or ""
                return output_text.strip()

            response = self.openai_client.responses.create(model=self.llm_model, input=prompt)
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

    def _format_evidence_for_llm(self, evidence_blocks: list[tuple[str, float, str]]) -> str:
        blocks = []
        for index, (file_name, score, text) in enumerate(evidence_blocks[:4], start=1):
            blocks.append(
                f"[Fuente {index}] Documento: {file_name} | relevancia: {score}\n{text[:1400]}"
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
        self, evidence_blocks: list[tuple[str, float, str]], keywords: set[str]
    ) -> list[dict]:
        insights: list[dict] = []
        seen = set()

        for file_name, score, text in evidence_blocks:
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

    def _build_overview(self, question: str, insights: list[dict], keywords: set[str]) -> str:
        question_style = self._question_style(question)
        primary_topics = self._collect_topics(insights, keywords)
        topic_text = ", ".join(primary_topics[:3])

        if question_style == "como":
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

    def _build_conclusion(self, question: str, insights: list[dict], keywords: set[str]) -> str:
        if not insights:
            return ""

        dominant_topics = self._collect_topics(insights, keywords)
        top_summary = insights[0]["summary"]
        if dominant_topics:
            return (
                f"En conjunto, la evidencia sugiere que el tema se entiende mejor si se consideran especialmente {', '.join(dominant_topics[:3])}, "
                f"y que {self._lowercase_first(top_summary)}"
            )
        return self._ensure_sentence(top_summary)

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
