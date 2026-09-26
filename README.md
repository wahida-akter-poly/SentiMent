# SENTI-MIND

SENTI-MIND is an API-backed sentiment workspace. FastAPI serves the HTML/CSS/JS
pages, and SQLite stores successful model-backed analyses. A saved analysis
contains document sentiment, independent sentence predictions, final Mixed
derivation, aspect sentiment, topics, supporting evidence, and a deterministic
summary. Batch CSV import, filtered history, filtered CSV export, and
database-derived dashboard analytics are included.

There are no seed reviews, fallback predictions, or fabricated dashboard
metrics. No trained model artifact or labeled training dataset is currently
bundled. Until a real artifact is supplied, the interface reports **Model Not
Trained** and `POST /api/analyze` returns `503 MODEL_UNAVAILABLE`.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/>. The API is documented at `/docs`.

## Train the baseline

Provide a real UTF-8 CSV with `Review,Label` columns. Labels are learned from
the supplied dataset (the script does not convert a binary dataset into a
three-class model). Empty rows and duplicate reviews are rejected to prevent
leakage and ambiguous training records.

```powershell
python train_baseline.py path\to\labeled_reviews.csv --output artifacts\baseline.joblib
```

The script trains a reproducible TF-IDF + logistic-regression pipeline, reports
held-out accuracy and macro-F1, and writes the model artifact. Set
`SENTI_MIND_MODEL_PATH` if the artifact is elsewhere. Restart the API after
training so it reloads the artifact.

## API

- `GET /api/health` — liveness and model availability
- `GET /api/model/status` — loaded model metadata or the honest unavailable reason
- `POST /api/analyze` — `{ "text": "...", "source": "optional" }`
- `POST /api/batch/analyze` — `{ "items": [{ "text": "...", "source": "..." }] }`, up to 50 per request
- `POST /api/analyses/upload` — CSV upload API
- `GET /api/analyses?limit=25&offset=0&sentiment=&source=&q=&start=&end=` — filtered persisted results
- `GET /api/analyses/export.csv` — filtered CSV export
- `GET /api/dashboard/summary` and `/api/analytics/summary` — DB-derived counts, percentages, confidence, sources, daily trend, aspects, topics, and negative-aspect complaints

`POST /api/analyze` persists one parent row only after the configured model
returns a prediction. Sentence and aspect inference use that same classifier.
Mixed is derived from confidently positive and negative sentence results; it is
not a classifier label or probability. Analytics return null percentages and
empty collections when there is no data. Batch Analysis is available at
`/pages/batch-analysis/` and sends CSV rows to `POST /api/batch/analyze`.

## Database and migrations

SQLAlchemy models live under `app/models`; Alembic is configured in
`alembic.ini`. `0001_create_analyses.py` creates the original table and
`0002_add_analysis_metadata.py` safely adds the intelligence fields. Apply with
`python -m alembic upgrade head`. The development lifespan also creates missing
tables for a first run; use Alembic for upgrades to an existing database.

## Tests

```powershell
pytest -q
```

Configuration can be copied from `.env.example`. Environment variables use the
`SENTI_MIND_` prefix.

See [DEMO-CHECKLIST.md](DEMO-CHECKLIST.md) for a no-fabricated-data demo
procedure and [FINAL-IMPLEMENTATION-STATUS.md](FINAL-IMPLEMENTATION-STATUS.md)
for current verification status and limitations.
