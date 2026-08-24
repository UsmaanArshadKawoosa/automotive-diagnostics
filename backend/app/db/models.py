import uuid
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, DateTime, Float, ForeignKey, Index, Integer, String, Text, TypeDecorator, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class UUIDListJSON(TypeDecorator):
    """JSONB list that stores UUID values as strings and restores UUID objects."""

    impl = JSONB
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return [str(item) for item in value]

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        restored: list[uuid.UUID] = []
        for item in value:
            if isinstance(item, uuid.UUID):
                restored.append(item)
            else:
                restored.append(uuid.UUID(str(item)))
        return restored

class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    vin: Mapped[str | None] = mapped_column(String(17), nullable=True, index=True)
    make: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symptom_text: Mapped[str] = mapped_column(Text, nullable=False)
    dtc_codes: Mapped[str | None] = mapped_column(Text, nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    results: Mapped[list["DiagnosticResult"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    conversation_messages: Mapped[list["DiagnosticConversationMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan", order_by="DiagnosticConversationMessage.turn_index")

class DiagnosticResult(Base):
    __tablename__ = "diagnostic_results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fault_description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    repair_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hypothesis_status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed", index=True)
    observed_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_checks: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    supporting_evidence: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    knowledge_references: Mapped[list[uuid.UUID] | None] = mapped_column(UUIDListJSON, nullable=True)
    session: Mapped["DiagnosticSession"] = relationship(back_populates="results")
    check_outcomes: Mapped[list["DiagnosticCheckOutcome"]] = relationship(back_populates="result", cascade="all, delete-orphan")


class DiagnosticCheckOutcome(Base):
    __tablename__ = "diagnostic_check_outcomes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("diagnostic_results.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    check_description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="recommended", index=True)
    observed_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    technician_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped["DiagnosticResult"] = relationship(back_populates="check_outcomes")


class DiagnosticConversationMessage(Base):
    __tablename__ = "diagnostic_conversation_messages"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    session: Mapped["DiagnosticSession"] = relationship(back_populates="conversation_messages")


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    __table_args__ = (
        Index(
            "ix_knowledge_entries_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entry_key: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', COALESCE(entry_key, '')), 'A') || "
            "setweight(to_tsvector('english', COALESCE(content, '')), 'B')",
            persisted=True,
        ),
        nullable=True,
    )


class ConfirmedDiagnosticCase(Base):
    __tablename__ = "confirmed_diagnostic_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    make: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    vin: Mapped[str | None] = mapped_column(String(17), nullable=True)
    symptom_text: Mapped[str] = mapped_column(Text, nullable=False)
    dtc_codes: Mapped[str | None] = mapped_column(Text, nullable=True)

    confirmed_fault: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_fault_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    repair_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)

    case_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)

    source_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_verified: Mapped[bool] = mapped_column(default=True, nullable=False)
