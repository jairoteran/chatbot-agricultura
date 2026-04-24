from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Pregunta del usuario")


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


class ReindexResponse(BaseModel):
    status: str
    detail: str
    indexed_files: list[str] = Field(default_factory=list)
