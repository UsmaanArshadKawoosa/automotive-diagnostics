import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DiagnosticResultBase(BaseModel):
    fault_description: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    repair_suggestion: str | None = None
    severity: str | None = None


class DiagnosticResultCreate(DiagnosticResultBase):
    pass


class DiagnosticResultRead(DiagnosticResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime


class DiagnosticSessionBase(BaseModel):
    vin: str | None = Field(default=None, max_length=17)
    make: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    year: int | None = Field(default=None, ge=1900, le=2100)
    symptom_text: str
    dtc_codes: str | None = None


class DiagnosticSessionCreate(DiagnosticSessionBase):
    pass


class DiagnosticSessionRead(DiagnosticSessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    results: list[DiagnosticResultRead] = []


class KnowledgeEntryBase(BaseModel):
    category: str = Field(max_length=50)
    entry_key: str | None = Field(default=None, max_length=100)
    content: str
    source: str | None = Field(default=None, max_length=255)
    meta: dict | None = None


class KnowledgeEntryCreate(KnowledgeEntryBase):
    embedding: list[float] | None = None


class KnowledgeEntryRead(KnowledgeEntryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    category: str | None = Field(default=None, max_length=50)
    top_k: int = Field(default=5, ge=1, le=50)


class KnowledgeSearchResult(BaseModel):
    id: uuid.UUID
    category: str
    entry_key: str | None
    content: str
    source: str | None
    similarity_score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeSearchResult]


class DiagnosticAnalyzeRequest(BaseModel):
    vin: str | None = Field(default=None, max_length=17)
    make: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    year: int | None = Field(default=None, ge=1900, le=2100)
    dtc_codes: list[str] | None = Field(default=None)
    symptom_text: str = Field(min_length=1, max_length=4000)

    def dtc_codes_text(self) -> str | None:
        if not self.dtc_codes:
            return None
        return ", ".join(self.dtc_codes)


class DiagnosticHypothesis(BaseModel):
    fault_description: str = Field(min_length=1)
    confidence_score: float = Field(ge=0.0, le=1.0)
    severity: str = Field(pattern=r"^(low|medium|high|critical)$")
    supporting_evidence: list[str]
    recommended_checks: list[str]
    repair_suggestion: str | None = None


class DiagnosticAnalyzeResponse(BaseModel):
    session_id: uuid.UUID
    vehicle: dict[str, str | int | None]
    query: str
    evidence: list[KnowledgeSearchResult]
    hypotheses: list[DiagnosticHypothesis]
