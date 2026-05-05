import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Boolean, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db import Base


def _utcnow() -> datetime:
    # Passed as a callable, not called here — SQLAlchemy invokes it per INSERT.
    return datetime.now(timezone.utc)


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    goal: Mapped[str] = mapped_column(Text)
    transcript: Mapped[str] = mapped_column(Text, default="")
    # Named "call_metadata" to avoid shadowing DeclarativeBase.metadata; stored as "metadata" in DB.
    call_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    analyses: Mapped[list["CallAnalysis"]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["HumanReview"]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )


class CallAnalysis(Base):
    __tablename__ = "call_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("calls.id", ondelete="CASCADE"), index=True
    )
    outcome: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_ai_response: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    call: Mapped["Call"] = relationship(back_populates="analyses")
    human_reviews: Mapped[list["HumanReview"]] = relationship(back_populates="analysis")


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("calls.id", ondelete="CASCADE"), index=True
    )
    analysis_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("call_analyses.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(16))  # accept | reject | modify
    final_outcome: Mapped[str] = mapped_column(String(64))
    notes: Mapped[str] = mapped_column(Text, default="")
    reviewer_name: Mapped[str] = mapped_column(String(128), default="")
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    call: Mapped["Call"] = relationship(back_populates="reviews")
    analysis: Mapped["CallAnalysis | None"] = relationship(back_populates="human_reviews")
