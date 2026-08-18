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
