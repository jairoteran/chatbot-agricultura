from __future__ import annotations

from io import BytesIO
import re
import unicodedata
from collections import Counter
from functools import lru_cache


SPANISH_STOP_WORDS = {
    "ademas", "algo", "algunos", "ante", "aunque", "cada", "como", "con", "contra",
    "cuando", "desde", "donde", "durante", "entre", "esta", "estas", "este", "estos",
    "hacia", "hasta", "para", "pero", "porque", "puede", "pueden", "segun", "sobre",
    "tambien", "tener", "tiene", "tienen", "todo", "todos", "tras", "unas", "unos",
    "agricultura", "documento", "documentos", "informacion", "sistema", "sistemas",
}

DOMAIN_TERMS = {
    "agroecologia", "agroecologico", "agricultura familiar", "agricultura organica",
    "agricultura tradicional", "saberes ancestrales", "conocimiento ancestral",
    "seguridad alimentaria", "soberania alimentaria", "cultivo", "cultivos", "suelo",
    "riego", "semilla", "semillas", "papa", "maiz", "quinua", "chocho", "amaranto",
    "camellones", "chakra", "chacra", "fertilizantes", "plagas", "enfermedades",
    "biodiversidad", "cambio climatico", "produccion agricola", "agricultura sostenible",
}

LOCATION_TERMS = {
    "ecuador", "tungurahua", "cotacachi", "cuenca", "san joaquin", "sierra norte",
    "galapagos", "costa", "sierra", "amazonia", "andes", "chimborazo", "cotopaxi",
    "pichincha", "imbabura", "loja", "azuay", "guayas", "manabi",
}

CORE_AGRI_TOKENS = {
    "agricola", "agricolas", "agricultura", "agroecologia", "agroecologico",
    "agroforestal", "agronomico", "alimento", "alimentos", "ancestral", "biocultural",
    "biodiversidad", "campesina", "chacra", "chakra", "climatico", "cosecha",
    "cultivo", "cultivos", "fertilidad", "fertilizante", "huerto", "maiz",
    "papa", "pasto", "plaga", "quinua", "riego", "semilla", "semillas",
    "siembra", "suelo", "sustentable", "tradicional",
}

UPLOAD_MIN_RELEVANCE_SCORE = 0.34
UPLOAD_MIN_TEXT_CHARS = 180


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _clean_text(text: str) -> str:
    cleaned = unicodedata.normalize("NFKC", str(text or ""))
    cleaned = cleaned.replace("\u00ad", "")
    cleaned = re.sub(r"(?<=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])-\s+(?=[a-záéíóúüñ])", "", cleaned)
    cleaned = re.sub(r"\b[a-záéíóúüñ]{2,6}-\s*\d{1,4}\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


@lru_cache(maxsize=1)
def _load_spacy_model():
    try:
        import spacy
    except Exception:
        return None, ""

    for model_name in ("es_core_news_sm", "es_core_news_md"):
        try:
            return spacy.load(model_name), model_name
        except Exception:
            continue

    try:
        nlp = spacy.blank("es")
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        return nlp, "spacy_blank_es"
    except Exception:
        return None, ""


def _top_domain_terms(normalized_text: str) -> list[str]:
    found = [term for term in DOMAIN_TERMS if term in normalized_text]
    return sorted(found, key=lambda term: (-len(term.split()), term))[:12]


def _top_location_terms(normalized_text: str) -> list[str]:
    return sorted(term for term in LOCATION_TERMS if term in normalized_text)[:10]


def _keyword_terms(cleaned_text: str) -> list[str]:
    normalized_text = _normalize_text(cleaned_text)
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]{4,}", normalized_text)
        if token not in SPANISH_STOP_WORDS
    ]
    counts = Counter(tokens)
    return [term for term, _ in counts.most_common(14)]


def _extract_pdf_text(content: bytes, max_pages: int = 18, max_chars: int = 24000) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""

    extracted_parts: list[str] = []
    try:
        reader = PdfReader(BytesIO(content))
        for page in reader.pages[:max_pages]:
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted_parts.append(page_text)
            if sum(len(part) for part in extracted_parts) >= max_chars:
                break
    except Exception:
        return ""

    return _clean_text(" ".join(extracted_parts))[:max_chars]


def _relevance_metrics(normalized_text: str, key_terms: list[str]) -> tuple[int, int, int]:
    domain_hits = sum(1 for term in DOMAIN_TERMS if term in normalized_text)
    location_hits = sum(1 for term in LOCATION_TERMS if term in normalized_text)
    agri_hits = sum(1 for term in key_terms if term in CORE_AGRI_TOKENS)
    return domain_hits, location_hits, agri_hits


def _relevance_score(normalized_text: str, key_terms: list[str], text_length: int) -> float:
    domain_hits, location_hits, agri_hits = _relevance_metrics(normalized_text, key_terms)
    score = 0.0
    score += min(domain_hits, 4) * 0.16
    score += min(location_hits, 3) * 0.08
    score += min(agri_hits, 5) * 0.1
    if text_length >= 900:
        score += 0.18
    elif text_length >= 400:
        score += 0.1
    elif text_length >= UPLOAD_MIN_TEXT_CHARS:
        score += 0.05
    return min(1.0, score)


def analyze_corpus_document(file_name: str, chunks: list[str]) -> dict:
    text = _clean_text(" ".join(chunks))[:18000]
    normalized_text = _normalize_text(text)
    topics = _top_domain_terms(normalized_text)
    entities = _top_location_terms(normalized_text)
    key_terms = _keyword_terms(text)
    analyzer = "fallback"
    model_name = ""

    nlp, model_name = _load_spacy_model()
    if nlp is not None and text:
        try:
            doc = nlp(text[: nlp.max_length - 1])
            analyzer = "spacy" if model_name != "spacy_blank_es" else "spacy_blank"
            if getattr(doc, "ents", None):
                entity_counts = Counter(
                    ent.text.strip()
                    for ent in doc.ents
                    if ent.text.strip() and len(ent.text.strip()) >= 3
                )
                entities = [item for item, _ in entity_counts.most_common(12)] or entities

            noun_chunks = getattr(doc, "noun_chunks", None)
            if noun_chunks is not None:
                chunk_counts = Counter()
                for chunk in noun_chunks:
                    value = _normalize_text(chunk.text).strip()
                    if len(value) >= 4 and value not in SPANISH_STOP_WORDS:
                        chunk_counts[value] += 1
                topics = [item for item, _ in chunk_counts.most_common(12)] or topics
        except Exception:
            analyzer = "fallback"

    if not topics:
        topics = key_terms[:8]

    return {
        "file_name": file_name,
        "topics": topics[:12],
        "entities": entities[:12],
        "key_terms": key_terms[:14],
        "nlp_analyzer": analyzer,
        "nlp_model": model_name,
    }


def inspect_uploaded_pdf(file_name: str, content: bytes) -> dict:
    text = _extract_pdf_text(content)
    if len(text) < UPLOAD_MIN_TEXT_CHARS:
        return {
            "accepted": False,
            "relevance_score": 0.0,
            "detail": (
                "No pude leer suficiente contenido util dentro del PDF. "
                "Prueba con un archivo mas legible o con texto seleccionable."
            ),
            "topics": [],
            "entities": [],
            "key_terms": [],
            "nlp_analyzer": "fallback",
            "nlp_model": "",
        }

    analysis = analyze_corpus_document(file_name, [text])
    normalized_text = _normalize_text(text)
    score = _relevance_score(normalized_text, analysis["key_terms"], len(text))
    domain_hits, location_hits, agri_hits = _relevance_metrics(normalized_text, analysis["key_terms"])
    accepted = score >= UPLOAD_MIN_RELEVANCE_SCORE and (domain_hits > 0 or agri_hits >= 2)

    if accepted:
        detail = (
            "Revise el documento automaticamente y quedo listo para indexarse."
        )
    else:
        detail = (
            "Revise el documento, pero no encontre suficiente contenido relacionado con agricultura "
            "o saberes ancestrales como para aceptarlo automaticamente."
        )

    return {
        "accepted": accepted,
        "relevance_score": round(score, 3),
        "detail": detail,
        "topics": analysis["topics"],
        "entities": analysis["entities"],
        "key_terms": analysis["key_terms"],
        "nlp_analyzer": analysis["nlp_analyzer"],
        "nlp_model": analysis["nlp_model"],
    }
