import os
import threading
from hashlib import sha256
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google.auth import default as google_auth_default
from google.auth.transport.requests import AuthorizedSession

from app.admin_auth import (
    AdminAuthError,
    create_admin_session_token,
    verify_admin_session_token,
    verify_google_identity_token,
)
from app.cloud_layout import get_cloud_layout
from app.corpus_analyzer import inspect_uploaded_pdf
from app.document_repository import create_document_repository
from app.metadata_repository import create_metadata_repository
from app.rag_service import RAGService
from app.settings import get_settings
from app.schemas import (
    AdminConfigResponse,
    AdminDocumentListResponse,
    AdminDocumentMutationResponse,
    AdminDocumentRecord,
    AdminDocumentUploadCompleteRequest,
    AdminDocumentUploadSessionRequest,
    AdminDocumentUploadSessionResponse,
    AdminGoogleSessionRequest,
    AdminSessionResponse,
    ChatRequest,
    ChatResponse,
    DocumentSummaryRequest,
    DocumentSummaryResponse,
    HealthResponse,
    ReindexResponse,
)
from app.metadata_models import DOCUMENT_STATUS_PENDING_INDEX, DocumentRecord

settings = get_settings()
cloud_layout = get_cloud_layout(settings)
document_repository = create_document_repository(settings, cloud_layout)
metadata_repository = create_metadata_repository(settings, cloud_layout)


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
init_progress = 0
init_stage = "starting"
init_detail = "Inicializando servicio..."


def _admin_auth_guard() -> None:
    if not settings.admin_auth_enabled:
        raise HTTPException(
            status_code=503,
            detail=(
                "La gestion documental segura aun no esta configurada. "
                "Define GOOGLE_AUTH_CLIENT_ID, ADMIN_EMAILS y ADMIN_SESSION_SECRET."
            ),
        )


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Falta la sesion de gestion documental.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="La cabecera Authorization no es valida.")
    return token.strip()


def require_admin_session(authorization: str | None = Header(default=None)) -> AdminSessionResponse:
    _admin_auth_guard()
    token = _extract_bearer_token(authorization)
    try:
        session = verify_admin_session_token(
            token,
            secret=settings.admin_session_secret,
        )
    except AdminAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if session.email not in settings.admin_emails:
        raise HTTPException(status_code=403, detail="Tu cuenta no esta autorizada para gestionar el corpus documental.")

    return AdminSessionResponse(
        authenticated=True,
        email=session.email,
        display_name="",
        picture_url="",
        expires_at=session.expires_at,
        session_token="",
    )


def _document_record_payload(item, metadata: DocumentRecord | None = None) -> AdminDocumentRecord:
    return AdminDocumentRecord(
        file_name=item.file_name,
        relative_path=item.relative_path,
        size=item.size,
        fingerprint=item.fingerprint,
        status=metadata.status if metadata is not None else DOCUMENT_STATUS_PENDING_INDEX,
        topics=metadata.topics if metadata is not None else [],
        entities=metadata.entities if metadata is not None else [],
        key_terms=metadata.key_terms if metadata is not None else [],
        nlp_analyzer=metadata.nlp_analyzer if metadata is not None else "",
    )


def _document_storage_path(relative_path: str) -> str:
    if settings.uses_cloud_documents:
        from app.cloud_layout import get_cloud_layout

        return get_cloud_layout(settings).document_blob_path(relative_path)
    return f"local:{relative_path}"


def _fingerprint_bytes(content: bytes) -> str:
    digest = sha256()
    digest.update(content)
    return digest.hexdigest()


def _build_document_record_from_analysis(item, content: bytes, analysis: dict) -> DocumentRecord:
    return DocumentRecord(
        document_id=(item.fingerprint or _fingerprint_bytes(content))[:24],
        file_name=item.file_name,
        relative_path=item.relative_path,
        storage_path=_document_storage_path(item.relative_path),
        fingerprint=item.fingerprint or _fingerprint_bytes(content),
        size=item.size,
        status=DOCUMENT_STATUS_PENDING_INDEX,
        topics=analysis.get("topics", []),
        entities=analysis.get("entities", []),
        key_terms=analysis.get("key_terms", []),
        nlp_analyzer=analysis.get("nlp_analyzer", ""),
    )


def _trigger_cloud_run_reindex_job() -> dict:
    if not settings.cloud_project_id:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT es obligatorio para ejecutar el job de reindexado.")

    total_documents = len(document_repository.list_pdf_files())
    dispatch_job_id = metadata_repository.start_reindex_job(
        trigger="admin-panel",
        source="cloud-run-dispatch",
        total_documents=total_documents,
    )
    metadata_repository.update_reindex_progress(
        dispatch_job_id,
        progress=0,
        stage="queued",
        detail="Solicitud enviada al Cloud Run Job de reindexado.",
        total_documents=total_documents,
    )

    credentials, _ = google_auth_default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    job_resource = (
        f"projects/{settings.cloud_project_id}/locations/{settings.cloud_region}/jobs/{settings.reindex_job_name}"
    )
    response = session.post(
        f"https://run.googleapis.com/v2/{job_resource}:run",
        json={},
        timeout=30,
    )
    payload = {}
    try:
        payload = response.json()
    except Exception:
        payload = {}

    if response.status_code >= 400:
        metadata_repository.finish_reindex_job(
            dispatch_job_id,
            status="failed",
            error_message=(
                payload.get("error", {}).get("message")
                or payload.get("message")
                or "No fue posible ejecutar el Cloud Run Job de reindexado."
            ),
        )
        error_message = (
            payload.get("error", {}).get("message")
            or payload.get("message")
            or "No fue posible ejecutar el Cloud Run Job de reindexado."
        )
        raise RuntimeError(error_message)

    execution_name = payload.get("name", "")
    metadata_repository.update_reindex_progress(
        dispatch_job_id,
        progress=1,
        stage="queued",
        detail=(
            f"Job aceptado por Cloud Run. Ejecucion: {execution_name.split('/')[-1]}"
            if execution_name
            else "Job aceptado por Cloud Run. Esperando que inicie la ejecucion."
        ),
        total_documents=total_documents,
    )

    return {
        "status": "ok",
        "detail": "Reindexado lanzado correctamente desde el panel de gestion documental.",
        "indexed_files": [],
        "indexed_documents": [],
        "index_source": "cloud-run-job",
        "last_index_seconds": 0.0,
        "job_name": execution_name,
    }


def update_init_state(progress: int, stage: str, detail: str) -> None:
    global init_progress, init_stage, init_detail
    init_progress = max(0, min(progress, 100))
    init_stage = stage
    init_detail = detail


def initialize_service(force_rebuild: bool = False) -> None:
    global rag_service, startup_error

    try:
        if rag_service is None:
            update_init_state(2, "starting", "Inicializando servicio...")
            rag_service = RAGService(progress_callback=update_init_state)
        elif force_rebuild:
            update_init_state(12, "reindexing", "Reconstruyendo el indice documental...")
            rag_service.reindex()
            update_init_state(100, "ready", "Servicio listo")
        startup_error = None
    except Exception as exc:
        rag_service = None
        startup_error = str(exc)
        update_init_state(0, "error", startup_error)


def ensure_service_initializing(force_rebuild: bool = False) -> None:
    global init_thread

    if rag_service is not None and not force_rebuild:
        return

    if settings.deployment_target == "cloud-run":
        with init_lock:
            if rag_service is not None and not force_rebuild:
                return
            initialize_service(force_rebuild=force_rebuild)
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
    if settings.deployment_target == "cloud-run":
        return
    ensure_service_initializing(force_rebuild=False)


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    if rag_service is None:
        ensure_service_initializing(force_rebuild=False)
        if rag_service is not None:
            return HealthResponse(**rag_service.get_status())
        return HealthResponse(
            status="checking" if startup_error is None else "error",
            detail=startup_error or init_detail,
            init_stage=init_stage,
            init_progress=init_progress,
            indexed_files=[],
            indexed_file_count=0,
            index_ready=False,
        )

    return HealthResponse(**rag_service.get_status())


@app.get("/admin/config", response_model=AdminConfigResponse)
def admin_config() -> AdminConfigResponse:
    return AdminConfigResponse(
        enabled=settings.admin_auth_enabled,
        provider="google",
        client_id=settings.google_auth_client_id if settings.admin_auth_enabled else "",
        admin_base_path=settings.admin_base_path,
        session_ttl_seconds=settings.admin_session_ttl_seconds if settings.admin_auth_enabled else 0,
    )


@app.post("/admin/session/google", response_model=AdminSessionResponse)
def create_admin_google_session(payload: AdminGoogleSessionRequest) -> AdminSessionResponse:
    _admin_auth_guard()
    try:
        identity = verify_google_identity_token(
            payload.credential,
            client_id=settings.google_auth_client_id,
        )
    except AdminAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if identity.email not in settings.admin_emails:
        raise HTTPException(status_code=403, detail="Tu cuenta no esta autorizada para gestionar el corpus documental.")

    session_token, expires_at = create_admin_session_token(
        identity.email,
        secret=settings.admin_session_secret,
        ttl_seconds=settings.admin_session_ttl_seconds,
    )
    return AdminSessionResponse(
        authenticated=True,
        email=identity.email,
        display_name=identity.display_name,
        picture_url=identity.picture_url,
        expires_at=expires_at,
        session_token=session_token,
    )


@app.get("/admin/session", response_model=AdminSessionResponse)
def get_admin_session(session: AdminSessionResponse = Depends(require_admin_session)) -> AdminSessionResponse:
    return session


@app.get("/admin/documents", response_model=AdminDocumentListResponse)
def list_admin_documents(_: AdminSessionResponse = Depends(require_admin_session)) -> AdminDocumentListResponse:
    records = document_repository.list_pdf_files()
    metadata_by_path = {
        item.relative_path: item
        for item in metadata_repository.list_document_records()
    }
    return AdminDocumentListResponse(
        documents=[_document_record_payload(item, metadata_by_path.get(item.relative_path)) for item in records],
        total_documents=len(records),
        source=document_repository.describe_source(),
    )


@app.post("/admin/documents", response_model=AdminDocumentMutationResponse)
async def upload_admin_document(
    file: UploadFile = File(...),
    session: AdminSessionResponse = Depends(require_admin_session),
) -> AdminDocumentMutationResponse:
    file_name = (file.filename or "").strip()
    if not file_name:
        raise HTTPException(status_code=400, detail="Debes seleccionar un archivo PDF valido.")
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo PDF esta vacio.")

    analysis = inspect_uploaded_pdf(file_name, content)
    if not analysis.get("accepted"):
        raise HTTPException(
            status_code=400,
            detail=analysis.get("detail") or "No pude aceptar el documento automaticamente.",
        )

    record = document_repository.upload_pdf(file_name, content)
    document_metadata = _build_document_record_from_analysis(record, content, analysis)
    metadata_repository.upsert_document_record(document_metadata)
    return AdminDocumentMutationResponse(
        status="ok",
        detail=f"Documento '{record.file_name}' subido correctamente. {analysis.get('detail', '')}".strip(),
        document=_document_record_payload(record, document_metadata),
    )


@app.post("/admin/documents/upload-session", response_model=AdminDocumentUploadSessionResponse)
def create_admin_document_upload_session(
    payload: AdminDocumentUploadSessionRequest,
    origin: str | None = Header(default=None),
    _: AdminSessionResponse = Depends(require_admin_session),
) -> AdminDocumentUploadSessionResponse:
    file_name = payload.file_name.strip()
    if not file_name:
        raise HTTPException(status_code=400, detail="Debes seleccionar un archivo PDF valido.")
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF.")
    if not settings.uses_cloud_documents:
        raise HTTPException(
            status_code=400,
            detail="La subida directa para archivos pesados solo esta disponible cuando DOCUMENT_STORAGE_BACKEND=gcs.",
        )

    try:
        upload_url, relative_path = document_repository.create_upload_session(
            file_name=file_name,
            content_type=payload.content_type,
            size=payload.size,
            origin=(origin or "").strip(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AdminDocumentUploadSessionResponse(
        status="ok",
        detail="Sesion de subida creada correctamente.",
        upload_url=upload_url,
        relative_path=relative_path,
        file_name=Path(relative_path).name,
    )


@app.post("/admin/documents/complete", response_model=AdminDocumentMutationResponse)
def complete_admin_document_upload(
    payload: AdminDocumentUploadCompleteRequest,
    _: AdminSessionResponse = Depends(require_admin_session),
) -> AdminDocumentMutationResponse:
    normalized_path = payload.relative_path.strip().strip("/")
    if not normalized_path:
        raise HTTPException(status_code=400, detail="La ruta del documento no es valida.")

    try:
        record = document_repository.get_pdf_record(normalized_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontro el documento recien subido en el almacenamiento configurado.",
        )

    try:
        content = document_repository.read_pdf_bytes(normalized_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="No se pudo leer el documento recien subido para validarlo.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    analysis = inspect_uploaded_pdf(record.file_name, content)
    if not analysis.get("accepted"):
        try:
            document_repository.delete_pdf(normalized_path)
        except Exception:
            pass
        raise HTTPException(
            status_code=400,
            detail=analysis.get("detail") or "No pude aceptar el documento automaticamente.",
        )

    document_metadata = _build_document_record_from_analysis(record, content, analysis)
    metadata_repository.upsert_document_record(document_metadata)
    return AdminDocumentMutationResponse(
        status="ok",
        detail=f"Documento '{record.file_name}' subido correctamente. {analysis.get('detail', '')}".strip(),
        document=_document_record_payload(record, document_metadata),
    )


@app.delete("/admin/documents/{relative_path:path}", response_model=AdminDocumentMutationResponse)
def delete_admin_document(
    relative_path: str,
    _: AdminSessionResponse = Depends(require_admin_session),
) -> AdminDocumentMutationResponse:
    normalized_path = relative_path.strip().strip("/")
    if not normalized_path:
        raise HTTPException(status_code=400, detail="La ruta del documento no es valida.")

    existing = next(
        (item for item in document_repository.list_pdf_files() if item.relative_path == normalized_path),
        None,
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="No se encontro el documento solicitado.")

    document_repository.delete_pdf(normalized_path)
    metadata_repository.delete_document_record(normalized_path)
    return AdminDocumentMutationResponse(
        status="ok",
        detail=f"Documento '{existing.file_name}' eliminado correctamente.",
        document=_document_record_payload(existing),
    )


@app.post("/reindex", response_model=ReindexResponse)
def reindex(_: AdminSessionResponse = Depends(require_admin_session)) -> ReindexResponse:
    if settings.deployment_target == "cloud-run" and not settings.allow_runtime_reindex:
        try:
            result = _trigger_cloud_run_reindex_job()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return ReindexResponse(**result)

    if rag_service is None:
        ensure_service_initializing(force_rebuild=False)
        if rag_service is not None:
            result = rag_service.reindex()
            return ReindexResponse(**result)
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
        if rag_service is not None:
            history = [message.model_dump() for message in payload.history]
            result = rag_service.query(
                payload.question,
                history=history,
                response_style=payload.response_style,
            )
            return ChatResponse(**result)
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
        if rag_service is not None:
            result = rag_service.summarize_document(
                payload.file_name,
                response_style=payload.response_style,
            )
            return DocumentSummaryResponse(**result)
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
