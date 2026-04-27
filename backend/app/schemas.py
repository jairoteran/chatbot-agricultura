from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Pregunta del usuario")
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)


class SourceChunk(BaseModel):
    file_name: str
    score: float
    text: str


class ChatResponse(BaseModel):
    answer: str
    found: bool
    sources: list[SourceChunk] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    detail: str
    indexed_files: list[str] = Field(default_factory=list)
    indexed_file_count: int = 0
    index_ready: bool = False
    index_source: str = "startup"
    last_index_seconds: float = 0.0
    embed_model: str = ""
    response_mode: str = "extractive"
    llm_model: str = ""


class ReindexResponse(BaseModel):
    status: str
    detail: str
    indexed_files: list[str] = Field(default_factory=list)
    index_source: str = "rebuild"
    last_index_seconds: float = 0.0
