# SENTI-MIND Demo Checklist

## Before the demo

- [ ] Install dependencies in the project virtual environment.
- [ ] Run `python -m alembic upgrade head` and confirm Alembic is at `0002_add_analysis_metadata`.
- [ ] Start the service with `python -m uvicorn app.main:app --reload`.
- [ ] Open `/api/model/status`. Confirm the model state and metadata reflect the configured artifact; do not present unavailable fields as measured values.
- [ ] If the status is `Model Not Trained`, explain that predictions are disabled. Do not use fabricated reviews, seeded records, or synthetic metrics.
- [ ] To demonstrate inference, configure a legitimately trained artifact built from a real, labeled dataset with `SENTI_MIND_MODEL_PATH`, then restart and recheck model status.
- [ ] Open `/pages/batch-analysis/` and use a real CSV with a `Review` column and optional `Source` column. The downloadable template contains headers only.

## Verify the workflow

- [ ] Submit one real review in Text Analysis and verify it creates one saved analysis.
- [ ] Confirm sentence results, Mixed derivation, aspects, topics, evidence, and summary reflect the configured model output.
- [ ] Import a CSV and verify successful rows are saved, source values are retained, and skipped rows are reported.
- [ ] Filter history by sentiment, source, search text, start date, and end date.
- [ ] Check dashboard and analytics counts, source volume, daily trend, aspects, topics, and complaint counts against saved records.
- [ ] Export CSV and confirm the selected date range is respected.
- [ ] Keep the database empty if no legitimate data is available; empty-state metrics are expected and honest.
