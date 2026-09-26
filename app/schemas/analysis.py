from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


Sentiment = Literal["positive", "neutral", "negative"]


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    source: str | None = Field(default=None, max_length=80)

    @field_validator("text")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text must contain non-whitespace characters.")
        return value


class AnalysisResponse(BaseModel):
    id: int
    text: str
    source: str | None
    sentiment: str
    model_sentiment: str
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[str, float]
    sentence_results: list[dict[str, object]] | None = None
    aspects: list[dict[str, object]] | None = None
    topics: list[str] | None = None
    evidence: dict[str, object] | list[dict[str, object]] | None = None
    summary_text: str | None = None
    model_version: str
    created_at: datetime


class AnalysisListResponse(BaseModel):
    items: list[AnalysisResponse]
    total: int


class AnalyzeBatchItem(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    source: str | None = Field(default=None, max_length=80)

    @field_validator("text")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text must contain non-whitespace characters.")
        return value


class AnalyzeBatchRequest(BaseModel):
    items: list[AnalyzeBatchItem] = Field(min_length=1, max_length=50)


class BatchAnalysisResponse(BaseModel):
    items: list[AnalysisResponse]
    total: int
    processed: int = 0
    skipped: int = 0
    errors: list[dict[str, object]] = Field(default_factory=list)


class ModelStatusResponse(BaseModel):
    available: bool
    model_version: str | None = None
    labels: list[str] = Field(default_factory=list)
    reason: str | None = None
    accuracy: float | None = None
    macro_f1: float | None = None
    train_rows: int | None = None
    test_rows: int | None = None


class SummaryResponse(BaseModel):
    has_data: bool
    total: int
    counts: dict[str, int]
    percentages: dict[str, float | None]
    average_confidence: float | None
    by_source: list[dict[str, object]]
    trend: list[dict[str, object]]
    top_aspects: list[dict[str, object]] | None = None
    top_topics: list[dict[str, object]] | None = None
    top_complaints: list[dict[str, object]] | None = None
