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


class DocumentCategory(BaseModel):
    label: str
    documents: list[IndexedDocument] = Field(default_factory=list)


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
    document_categories: list[DocumentCategory] = Field(default_factory=list)
    last_interaction_label: str = "Sin consultas"
    last_response_ms: int = 0
    last_input_tokens: int = 0
    last_output_tokens: int = 0
    last_total_tokens: int = 0


class ReindexResponse(BaseModel):
    status: str
    detail: str
    indexed_files: list[str] = Field(default_factory=list)
    indexed_documents: list[IndexedDocument] = Field(default_factory=list)
    document_categories: list[DocumentCategory] = Field(default_factory=list)
    index_source: str = "rebuild"
    last_index_seconds: float = 0.0


class DocumentSummaryRequest(BaseModel):
    file_name: str = Field(..., min_length=1, description="Nombre del documento")
    response_style: str = Field(
        default="academico",
        pattern=RESPONSE_STYLE_PATTERN,
        description="Estilo de resumen: academico, simple o tecnico",
    )


class CompareDocumentsRequest(BaseModel):
    file_names: list[str] = Field(..., min_length=2, max_length=4)
    response_style: str = Field(
        default="academico",
        pattern=RESPONSE_STYLE_PATTERN,
        description="Estilo de comparacion: academico, simple o tecnico",
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


class CompareDocumentsResponse(BaseModel):
    answer: str
    found: bool
    compared_documents: list[IndexedDocument] = Field(default_factory=list)
    sources: list[SourceChunk] = Field(default_factory=list)
    response_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
