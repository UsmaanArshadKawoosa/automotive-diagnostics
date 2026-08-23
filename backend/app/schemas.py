import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_DTC_PATTERN = re.compile(r"^[PCBU][0-9]{4}$")


class DiagnosticResultBase(BaseModel):
    fault_description: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    repair_suggestion: str | None = None
    severity: str | None = None
    hypothesis_status: str = Field(default="proposed", pattern=r"^(proposed|investigating|confirmed|rejected)$")
    observed_result: str | None = None
    recommended_checks: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    knowledge_references: list[uuid.UUID] = Field(default_factory=list)

    @field_validator(
        "recommended_checks", "supporting_evidence", "knowledge_references", mode="before"
    )
    @classmethod
    def _empty_if_none(cls, value: object) -> object:
        return [] if value is None else value


class DiagnosticResultCreate(DiagnosticResultBase):
    pass


class DiagnosticResultRead(DiagnosticResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime
    check_outcomes: list["DiagnosticCheckOutcomeRead"] = []


class DiagnosticCheckOutcomeBase(BaseModel):
    check_description: str = Field(min_length=1)
    status: str = Field(default="recommended", pattern=r"^(recommended|performed|passed|failed)$")
    observed_result: str | None = None
    technician_note: str | None = None


class DiagnosticCheckOutcomeCreate(DiagnosticCheckOutcomeBase):
    pass


class DiagnosticCheckOutcomeUpdate(BaseModel):
    status: str | None = Field(default=None, pattern=r"^(recommended|performed|passed|failed)$")
    observed_result: str | None = None
    technician_note: str | None = None


class DiagnosticCheckOutcomeRead(DiagnosticCheckOutcomeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    result_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DiagnosticSessionBase(BaseModel):
    vin: str | None = Field(default=None, max_length=17)
    make: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    year: int | None = Field(default=None, ge=1900, le=2100)
    symptom_text: str
    dtc_codes: str | None = None
    vehicle_type: str | None = Field(default=None, pattern=r"^(hatchback|sedan|suv|pickup|van)$")

    @field_validator("vin")
    @classmethod
    def _validate_vin(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.upper()
        if len(value) != 17:
            raise ValueError("VIN must be exactly 17 characters")
        for char in ("I", "O", "Q"):
            if char in value:
                raise ValueError(f"VIN cannot contain '{char}'")
        return value


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


class KnowledgeBulkIngestRequest(BaseModel):
    entries: list[KnowledgeEntryCreate] = Field(min_length=1, max_length=100)


class KnowledgeBulkIngestResponse(BaseModel):
    created: int
    skipped: int
    errors: list[str]


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


class EvidenceReference(BaseModel):
    """Structured reference to a specific piece of retrieved evidence."""
    evidence_id: uuid.UUID
    category: str
    entry_key: str | None
    excerpt: str
    similarity_score: float
    relevance: str = Field(default="supporting", pattern=r"^(supporting|conflicting|contextual)$")


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeSearchResult]


class DiagnosticAnalyzeRequest(BaseModel):
    vin: str | None = Field(default=None, max_length=17)
    make: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    year: int | None = Field(default=None, ge=1900, le=2100)
    vehicle_type: str | None = Field(default=None, pattern=r"^(hatchback|sedan|suv|pickup|van)$")
    dtc_codes: list[str] | None = Field(default=None)
    symptom_text: str = Field(min_length=1, max_length=4000)
    session_id: uuid.UUID | None = Field(default=None)
    follow_up_answer: str | None = Field(default=None, max_length=4000)

    @field_validator("vin")
    @classmethod
    def _validate_vin(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.upper()
        if len(value) != 17:
            raise ValueError("VIN must be exactly 17 characters")
        for char in ("I", "O", "Q"):
            if char in value:
                raise ValueError(f"VIN cannot contain '{char}'")
        return value

    @field_validator("dtc_codes")
    @classmethod
    def _validate_dtc_codes(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if len(value) == 0:
            raise ValueError("At least one DTC code is required when provided")
        normalized: list[str] = []
        seen: set[str] = set()
        for code in value:
            if not isinstance(code, str):
                raise ValueError("DTC codes must be strings")
            code = code.strip().upper()
            if not code:
                raise ValueError("DTC code must not be empty")
            if code in seen:
                continue
            if not _DTC_PATTERN.match(code):
                raise ValueError(f"Invalid DTC code: {code}")
            seen.add(code)
            normalized.append(code)
        return normalized

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
    knowledge_references: list[uuid.UUID] = Field(default_factory=list)
    component_id: str | None = None
    system_category: str | None = None
    vehicle_region: str | None = None
    safety_tier: str | None = None
    safety_tier_label: str | None = None
    safety_tier_description: str | None = None
    safety_tier_reasoning: list[str] = Field(default_factory=list)
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    differential_rank: int | None = None
    evidence_quality: str | None = Field(default=None, pattern=r"^(strong|moderate|weak|insufficient)$")


class RepairSafetyTier(BaseModel):
    tier: str = Field(pattern=r"^(diy_inspection|diy_repair|mechanic_recommended|immediate_professional)$")
    label: str
    description: str


# TODO: Integrate RepairSafetyTier into DiagnosticHypothesis once the rules engine is implemented.
# The tier should be derived from severity, component type, and repair complexity,
# NOT generated freely by the LLM.


class DiagnosticAnalyzeResponse(BaseModel):
    session_id: uuid.UUID
    vehicle: dict[str, str | int | None]
    query: str
    evidence: list[KnowledgeSearchResult]
    hypotheses: list[DiagnosticHypothesis]
    status: str = Field(pattern=r"^(complete|needs_more_information)$")
    follow_up_question: str | None = None
    follow_up_reason: str | None = None


class HypothesisOutcomeUpdate(BaseModel):
    hypothesis_status: str = Field(pattern=r"^(proposed|investigating|confirmed|rejected)$")
    observed_result: str | None = None


class DiagnosticConversationMessageBase(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str
    turn_index: int


class DiagnosticConversationMessageCreate(DiagnosticConversationMessageBase):
    pass


class DiagnosticConversationMessageRead(DiagnosticConversationMessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime


class DiagnosticSessionRead(DiagnosticSessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    results: list[DiagnosticResultRead] = []
    conversation_messages: list[DiagnosticConversationMessageRead] = []
