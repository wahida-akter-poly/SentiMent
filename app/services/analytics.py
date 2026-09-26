from datetime import date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Analysis


def summary(
    session: Session,
    start: date | None = None,
    end: date | None = None,
    source: str | None = None,
    sentiment: str | None = None,
    q: str | None = None,
) -> dict:
    filters = []
    if start:
        filters.append(Analysis.created_at >= datetime.combine(start, datetime.min.time()))
    if end:
        filters.append(Analysis.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()))
    if source:
        source_value = source.strip()
        if source_value:
            filters.append(func.lower(Analysis.source).like(f"%{source_value.lower()}%"))
    if sentiment:
        sentiment_value = sentiment.strip().lower()
        if sentiment_value in {"positive", "neutral", "negative", "mixed"}:
            filters.append(Analysis.sentiment == sentiment_value)
    if q and q.strip():
        search = f"%{q.strip()}%"
        filters.append(or_(Analysis.text.ilike(search), Analysis.summary_text.ilike(search)))

    rows = session.scalars(select(Analysis).where(*filters).order_by(Analysis.created_at.asc())).all()
    counts = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
    for row in rows:
        if row.sentiment in counts:
            counts[row.sentiment] += 1
    if sentiment and sentiment.strip().lower() not in counts:
        counts = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
    total = len(rows)
    percentages = {
        label: round(count / total * 100, 2) if total else None
        for label, count in counts.items()
    }
    source_label = func.coalesce(Analysis.source, "unspecified")
    source_rows = session.execute(
        select(source_label, func.count(Analysis.id))
        .where(*filters)
        .group_by(source_label)
        .order_by(func.count(Analysis.id).desc())
    ).all()
    trend: dict[str, dict[str, int]] = {}
    for row in rows:
        day = row.created_at.date().isoformat()
        trend.setdefault(day, {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0})
        trend[day].setdefault(row.sentiment, 0)
        trend[day][row.sentiment] += 1

    aspect_counts: dict[str, int] = {}
    topic_counts: dict[str, int] = {}
    complaint_counts: dict[str, int] = {}
    for row in rows:
        for item in row.aspects or []:
            if not isinstance(item, dict) or not item.get("aspect"):
                continue
            aspect = str(item["aspect"])
            aspect_counts[aspect] = aspect_counts.get(aspect, 0) + 1
            if item.get("sentiment") == "negative":
                complaint_counts[aspect] = complaint_counts.get(aspect, 0) + 1
        for topic in row.topics or []:
            if isinstance(topic, str) and topic:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

    def ranked(counts: dict[str, int]) -> list[dict[str, object]]:
        return [
            {"name": name, "count": count}
            for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
        ]

    return {
        "has_data": total > 0,
        "total": total,
        "counts": counts,
        "percentages": percentages,
        "average_confidence": round(sum(row.confidence for row in rows) / total, 4) if total else None,
        "by_source": [{"source": source, "count": count} for source, count in source_rows],
        "trend": [{"date": day, **values} for day, values in trend.items()],
        "top_aspects": ranked(aspect_counts),
        "top_topics": ranked(topic_counts),
        "top_complaints": ranked(complaint_counts),
    }
