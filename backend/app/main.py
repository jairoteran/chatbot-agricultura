import os
from pathlib import Path
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.rag_service import RAGService
from app.schemas import (
    ChatRequest,
    ChatResponse,
    DocumentSummaryRequest,
    DocumentSummaryResponse,
    HealthResponse,
    ReindexResponse,
)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _allowed_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "").strip()
    default_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    if not raw_origins:
        return default_origins

    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app = FastAPI(title="PDF Chat API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_service: RAGService | None = None
startup_error: str | None = None
init_lock = threading.Lock()
init_thread: threading.Thread | None = None


def initialize_service(force_rebuild: bool = False) -> None:
    global rag_service, startup_error

    try:
        if rag_service is None:
            rag_service = RAGService()
        elif force_rebuild:
            rag_service.reindex()
        startup_error = None
    except Exception as exc:
        rag_service = None
        startup_error = str(exc)


def ensure_service_initializing(force_rebuild: bool = False) -> None:
    global init_thread

    if rag_service is not None and not force_rebuild:
        return

    with init_lock:
        if init_thread is not None and init_thread.is_alive():
            return

        init_thread = threading.Thread(
            target=initialize_service,
            kwargs={"force_rebuild": force_rebuild},
            daemon=True,
        )
        init_thread.start()


@app.on_event("startup")
def startup_event() -> None:
    ensure_service_initializing(force_rebuild=False)


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    if rag_service is None:
        ensure_service_initializing(force_rebuild=False)
        return HealthResponse(
            status="checking" if startup_error is None else "error",
            detail=startup_error or "Inicializando servicio, cargando embeddings e indice documental...",
            indexed_files=[],
            indexed_file_count=0,
            index_ready=False,
        )

    return HealthResponse(**rag_service.get_status())


@app.post("/reindex", response_model=ReindexResponse)
def reindex() -> ReindexResponse:
    if rag_service is None:
        ensure_service_initializing(force_rebuild=False)
        raise HTTPException(
            status_code=503,
            detail=startup_error or "El servicio aun se esta inicializando. Intenta de nuevo en unos segundos.",
        )

    try:
        result = rag_service.reindex()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ReindexResponse(**result)


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    if rag_service is None:
        ensure_service_initializing(force_rebuild=False)
        raise HTTPException(
            status_code=503,
            detail=startup_error or "El servicio aun se esta inicializando. Espera a que /health indique que esta listo.",
        )

    try:
        history = [message.model_dump() for message in payload.history]
        result = rag_service.query(
            payload.question,
            history=history,
            response_style=payload.response_style,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(**result)


@app.post("/summarize-document", response_model=DocumentSummaryResponse)
def summarize_document(payload: DocumentSummaryRequest) -> DocumentSummaryResponse:
    if rag_service is None:
        ensure_service_initializing(force_rebuild=False)
        raise HTTPException(
            status_code=503,
            detail=startup_error or "El servicio aun se esta inicializando. Espera a que /health indique que esta listo.",
        )

    try:
        result = rag_service.summarize_document(
            payload.file_name,
            response_style=payload.response_style,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DocumentSummaryResponse(**result)
