from pydantic import BaseModel, Field

RESPONSE_STYLE_PATTERN = "^(academico|simple|tecnico)$"


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Pregunta del usuario")
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)
    response_style: str = Field(
        default="academico",
        pattern=RESPONSE_STYLE_PATTERN,
        description="Estilo de respuesta: academico, simple o tecnico",
    )


class SourceChunk(BaseModel):
    file_name: str
    display_title: str = ""
    page_label: str = ""
    score: float
    text: str


class IndexedDocument(BaseModel):
    file_name: str
    display_title: str


class ChatResponse(BaseModel):
    answer: str
    found: bool
    sources: list[SourceChunk] = Field(default_factory=list)
    response_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class HealthResponse(BaseModel):
    status: str
    detail: str
    init_stage: str = "starting"
    init_progress: int = 0
    indexed_files: list[str] = Field(default_factory=list)
    indexed_documents: list[IndexedDocument] = Field(default_factory=list)
    indexed_file_count: int = 0
    index_ready: bool = False
    index_source: str = "startup"
    last_index_seconds: float = 0.0
    embed_model: str = ""
    response_mode: str = "extractive"
    llm_provider: str = ""
    llm_model: str = ""
    deployment_mode: str = "local"
    allow_reindex: bool = True
    enable_vector_retrieval: bool = True
    document_storage_backend: str = "local"
    index_storage_backend: str = "local"
    metadata_backend: str = "none"
    process_state_backend: str = "none"
    documents_bucket: str = ""
    indexes_bucket: str = ""
    active_index_name: str = ""
    runtime_active_index_name: str = ""
    runtime_active_index_source: str = ""
    runtime_last_reindex_status: str = ""
    runtime_last_reindex_job_id: str = ""
    runtime_reindex_progress: int = 0
    runtime_reindex_stage: str = ""
    runtime_reindex_detail: str = ""
    runtime_reindex_total_documents: int = 0
    runtime_reindex_processed_documents: int = 0
    last_interaction_label: str = "Sin consultas"
    last_response_ms: int = 0
    last_input_tokens: int = 0
    last_output_tokens: int = 0
    last_total_tokens: int = 0
    last_generation_status: str = "not_used"
    last_generation_error: str = ""
    last_generation_model: str = ""


class ReindexResponse(BaseModel):
    status: str
    detail: str
    indexed_files: list[str] = Field(default_factory=list)
    indexed_documents: list[IndexedDocument] = Field(default_factory=list)
    index_source: str = "rebuild"
    last_index_seconds: float = 0.0


class DocumentSummaryRequest(BaseModel):
    file_name: str = Field(..., min_length=1, description="Nombre del documento")
    response_style: str = Field(
        default="academico",
        pattern=RESPONSE_STYLE_PATTERN,
        description="Estilo de resumen: academico, simple o tecnico",
    )


class DocumentSummaryResponse(BaseModel):
    file_name: str
    display_title: str = ""
    answer: str
    found: bool
    sources: list[SourceChunk] = Field(default_factory=list)
    response_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class AdminConfigResponse(BaseModel):
    enabled: bool
    provider: str = "google"
    client_id: str = ""
    admin_base_path: str = "/gestion"
    session_ttl_seconds: int = 0


class AdminGoogleSessionRequest(BaseModel):
    credential: str = Field(..., min_length=20, description="ID token emitido por Google Identity Services")


class AdminSessionResponse(BaseModel):
    authenticated: bool
    email: str = ""
    display_name: str = ""
    picture_url: str = ""
    expires_at: int = 0
    session_token: str = ""


class AdminDocumentRecord(BaseModel):
    file_name: str
    relative_path: str
    size: int
    fingerprint: str = ""
    status: str = "pending_index"
    topics: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    key_terms: list[str] = Field(default_factory=list)
    nlp_analyzer: str = ""


class AdminDocumentListResponse(BaseModel):
    documents: list[AdminDocumentRecord] = Field(default_factory=list)
    total_documents: int = 0
    source: str = ""


class AdminDocumentMutationResponse(BaseModel):
    status: str
    detail: str
    document: AdminDocumentRecord | None = None


class AdminDocumentUploadSessionRequest(BaseModel):
    file_name: str = Field(..., min_length=1)
    content_type: str = Field(default="application/pdf", min_length=1)
    size: int = Field(..., gt=0)


class AdminDocumentUploadSessionResponse(BaseModel):
    status: str
    detail: str
    upload_url: str
    relative_path: str
    file_name: str


class AdminDocumentUploadCompleteRequest(BaseModel):
    relative_path: str = Field(..., min_length=1)
