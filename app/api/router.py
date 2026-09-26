from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Analysis
from app.schemas.analysis import (
    AnalysisListResponse,
    AnalysisResponse,
    AnalyzeBatchRequest,
    AnalyzeRequest,
    BatchAnalysisResponse,
    ModelStatusResponse,
    SummaryResponse,
)
from app.services.analytics import summary
from app.services.model_adapter import ModelUnavailableError
from app.services.text_insights import build_analysis_payload

router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    adapter = request.app.state.model_adapter
    return {"status": "ok", "model": "available" if adapter.available else "unavailable"}


@router.get("/model/status", response_model=ModelStatusResponse)
def model_status(request: Request) -> ModelStatusResponse:
    adapter = request.app.state.model_adapter
    metrics = getattr(adapter, "metrics", {}) or {}
    return ModelStatusResponse(
        available=adapter.available,
        model_version=adapter.model_version,
        labels=adapter.labels,
        reason=adapter.reason,
        accuracy=metrics.get("accuracy"),
        macro_f1=metrics.get("macro_f1"),
        train_rows=metrics.get("train_rows"),
        test_rows=metrics.get("test_rows"),
    )


def _analysis_row(text: str, source: str | None, prediction) -> Analysis:
    if prediction.sentence_results is not None:
        payload = {
            "sentiment": prediction.sentiment,
            "model_sentiment": prediction.model_sentiment,
            "confidence": prediction.confidence,
            "probabilities": prediction.probabilities,
            "sentence_results": prediction.sentence_results,
            "aspects": prediction.aspects or [],
            "topics": prediction.topics or [],
            "evidence": prediction.evidence or {},
            "summary_text": prediction.summary_text,
        }
    else:
        payload = build_analysis_payload(text, prediction)
    return Analysis(
        text=text,
        source=source,
        sentiment=payload["sentiment"],
        model_sentiment=payload["model_sentiment"],
        confidence=payload["confidence"],
        probabilities=payload["probabilities"],
        sentence_results=payload["sentence_results"],
        aspects=payload["aspects"],
        topics=payload["topics"],
        evidence=payload["evidence"],
        summary_text=payload["summary_text"],
        model_version=prediction.model_version,
    )


@router.post("/analyze", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def analyze(payload: AnalyzeRequest, request: Request, session: Session = Depends(get_db)):
    adapter = request.app.state.model_adapter
    try:
        prediction = adapter.predict(payload.text)
    except ModelUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MODEL_UNAVAILABLE", "message": str(exc)},
        ) from exc

    row = _analysis_row(payload.text, payload.source, prediction)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("/analyses", response_model=AnalysisListResponse)
def analyses(
    session: Session = Depends(get_db),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    source: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
):
    filters = []
    if q:
        query_text = q.strip()
        if query_text:
            filters.append(or_(Analysis.text.ilike(f"%{query_text}%"), Analysis.summary_text.ilike(f"%{query_text}%")))
    if source:
        source_value = source.strip()
        if source_value:
            filters.append(Analysis.source.ilike(f"%{source_value}%"))
    if sentiment:
        sentiment_value = sentiment.strip().lower()
        if sentiment_value in {"positive", "neutral", "negative", "mixed"}:
            filters.append(Analysis.sentiment == sentiment_value)
    if start:
        start_date = _parse_date(start, "start")
        filters.append(Analysis.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end:
        end_date = _parse_date(end, "end")
        filters.append(Analysis.created_at < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))

    total = session.scalar(select(func.count()).select_from(Analysis).where(*filters)) or 0
    rows = session.scalars(
        select(Analysis).where(*filters).order_by(Analysis.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return {"items": rows, "total": total}


@router.post("/analyze/batch", response_model=BatchAnalysisResponse, status_code=status.HTTP_201_CREATED)
@router.post("/batch/analyze", response_model=BatchAnalysisResponse, status_code=status.HTTP_201_CREATED)
def analyze_batch(payload: AnalyzeBatchRequest, request: Request, session: Session = Depends(get_db)):
    adapter = request.app.state.model_adapter
    if not adapter.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MODEL_UNAVAILABLE", "message": str(adapter.reason or "Model is unavailable.")},
        )

    created: list[Analysis] = []
    errors: list[dict[str, object]] = []
    for index, item in enumerate(payload.items, start=1):
        try:
            prediction = adapter.predict(item.text)
            row = _analysis_row(item.text, item.source, prediction)
            session.add(row)
            created.append(row)
        except Exception as exc:  # pragma: no cover - captured for partial batch processing
            errors.append({"index": index, "text": item.text[:120], "error": str(exc)})
    session.commit()
    for row in created:
        session.refresh(row)
    return {"items": created, "total": len(created), "processed": len(created), "skipped": len(errors), "errors": errors}


def _parse_date(value: str | None, name: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{name} must be an ISO date (YYYY-MM-DD).") from exc


@router.get("/dashboard/summary", response_model=SummaryResponse)
def dashboard_summary(
    session: Session = Depends(get_db),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    source: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    return summary(session, _parse_date(start, "start"), _parse_date(end, "end"), source=source, sentiment=sentiment, q=q)


@router.get("/analytics/summary", response_model=SummaryResponse)
def analytics_summary(
    session: Session = Depends(get_db),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    source: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    return summary(session, _parse_date(start, "start"), _parse_date(end, "end"), source=source, sentiment=sentiment, q=q)


@router.get("/analyses/export")
@router.get("/analyses/export.csv")
def export_analyses(
    session: Session = Depends(get_db),
    format: str = Query(default="csv"),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    source: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    filters = []
    if start:
        start_date = _parse_date(start, "start")
        filters.append(Analysis.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end:
        end_date = _parse_date(end, "end")
        filters.append(Analysis.created_at < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))
    if source:
        cleaned = source.strip()
        if cleaned:
            filters.append(Analysis.source.ilike(f"%{cleaned}%"))
    if sentiment:
        cleaned = sentiment.strip().lower()
        if cleaned in {"positive", "neutral", "negative", "mixed"}:
            filters.append(Analysis.sentiment == cleaned)
    if q:
        cleaned = q.strip()
        if cleaned:
            filters.append(or_(Analysis.text.ilike(f"%{cleaned}%"), Analysis.summary_text.ilike(f"%{cleaned}%")))

    rows = session.scalars(select(Analysis).where(*filters).order_by(Analysis.created_at.desc())).all()
    if format.lower() != "csv":
        raise HTTPException(status_code=400, detail={"code": "UNSUPPORTED_FORMAT", "message": "Only CSV export is supported."})

    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "text", "source", "sentiment", "confidence", "model_version", "created_at"])
    for row in rows:
        writer.writerow([
            row.id,
            row.text,
            row.source or "",
            row.sentiment,
            row.confidence,
            row.model_version,
            row.created_at.isoformat(),
        ])
    output = buffer.getvalue().encode("utf-8")
    return Response(content=output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=senti_mind_analyses.csv"})


@router.post("/analyses/upload")
def upload_analyses(file: UploadFile, request: Request, session: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail={"code": "INVALID_FILE", "message": "Only CSV uploads are supported."})

    adapter = request.app.state.model_adapter
    if not adapter.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MODEL_UNAVAILABLE", "message": str(adapter.reason or "Model is unavailable.")},
        )

    import csv
    from io import StringIO

    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(StringIO(content))
    field_names = {field.strip().lower(): field for field in (reader.fieldnames or [])}
    accepted = set(field_names)
    if not reader.fieldnames or not ({"text", "review", "feedback"} & accepted):
        raise HTTPException(status_code=400, detail={"code": "INVALID_CSV", "message": "CSV must include a text column such as 'Review' or 'Text'."})

    created: list[Analysis] = []
    errors: list[dict[str, object]] = []
    for row in reader:
        text = next(
            (row.get(field_names[key], "") for key in ("text", "review", "feedback") if key in field_names),
            "",
        ).strip()
        if not text:
            continue
        source = row.get(field_names["source"]) if "source" in field_names else None
        source = source or "csv-upload"
        try:
            prediction = adapter.predict(text)
            saved = _analysis_row(text, source[:80], prediction)
            session.add(saved)
            created.append(saved)
        except Exception as exc:  # pragma: no cover - partial upload handling
            errors.append({"text": text[:120], "error": str(exc)})
    session.commit()
    for row in created:
        session.refresh(row)
    return {"items": created, "total": len(created), "processed": len(created), "skipped": len(errors), "errors": errors}
