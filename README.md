# SENTI-MIND

SENTI-MIND is an API-backed sentiment workspace. The existing vanilla HTML/CSS
pages are served by FastAPI, while SQLite stores only successful analyses.
There are no seed records, fallback predictions, or fabricated dashboard
metrics. Until a trained artifact exists, the analysis endpoint deliberately
returns `503 MODEL_UNAVAILABLE`.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/>. The API is documented at `/docs`.

## Train the baseline carefully

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
- `GET /api/analyses?limit=25&offset=0` — persisted results
- `GET /api/dashboard/summary` and `/api/analytics/summary` — calculated summaries

`POST /api/analyze` persists a row only after a model returns a prediction.
Analytics return null percentages and empty collections when there is no data.

## Database and migrations here

SQLAlchemy models live under `app/models`; Alembic is configured in
`alembic.ini` and the initial migration is `alembic/versions/0001_create_analyses.py`.
The development lifespan also creates missing tables for a first run.

## Tests here

```powershell
pytest -q
```

Configuration can be copied from `.env.example`. Environment variables use the
`SENTI_MIND_` prefix.
