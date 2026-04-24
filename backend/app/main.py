from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.rag_service import RAGService
from app.schemas import ChatRequest, ChatResponse, HealthResponse, ReindexResponse

app = FastAPI(title="PDF Chat API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_service: RAGService | None = None
startup_error: str | None = None


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


initialize_service()


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    if rag_service is None:
        return HealthResponse(
            status="error",
            detail=startup_error or "Servicio no disponible",
            indexed_files=[],
            indexed_file_count=0,
            index_ready=False,
        )

    return HealthResponse(**rag_service.get_status())


@app.post("/reindex", response_model=ReindexResponse)
def reindex() -> ReindexResponse:
    if rag_service is None:
        initialize_service(force_rebuild=False)
        if rag_service is None:
            raise HTTPException(status_code=503, detail=startup_error)

    try:
        result = rag_service.reindex()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ReindexResponse(**result)


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    if rag_service is None:
        raise HTTPException(status_code=503, detail=startup_error or "Servicio no disponible")

    try:
        result = rag_service.query(payload.question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(**result)
