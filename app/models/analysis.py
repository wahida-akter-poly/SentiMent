from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    model_sentiment: Mapped[str] = mapped_column(String(20), nullable=False, default="neutral")
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    probabilities: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    sentence_results: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    aspects: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    topics: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    evidence: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
