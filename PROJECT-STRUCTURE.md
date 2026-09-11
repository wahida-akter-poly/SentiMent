# SENTI-MIND Project Structure

Every feature page is self-contained: its `index.html`, CSS, and JavaScript are together in one meaningful folder.

```text
sentiment-dashboard/
├── index.html                         # Opens the Home page
├── pages/
│   ├── home/                          # Landing and navigation hub
│   │   ├── index.html
│   │   ├── home.css
│   │   └── home.js
│   ├── dashboard/                     # Overview charts and metrics
│   │   ├── index.html
│   │   ├── dashboard.css
│   │   └── dashboard.js
│   ├── text-analysis/                 # Sentiment detector
│   │   ├── index.html
│   │   ├── text-analysis.css
│   │   └── text-analysis.js
│   ├── analytics/                     # Detailed reporting
│   │   ├── index.html
│   │   ├── analytics.css
│   │   └── analytics.js
│   └── about-project/                 # Project description
│       ├── index.html
│       ├── about-project.css
│       └── about-project.js
└── assets/
    ├── styles/shared/app-shell.css    # Shared design system and responsive layout
    └── scripts/shared/app-interactions.js # Shared navigation, charts, and analysis logic

Backend additions:

```text
├── app/                         # FastAPI application, SQLAlchemy models, API, services
├── alembic/                     # Migration environment and schema revisions
├── train_baseline.py            # Real TF-IDF/logistic-regression training command
├── tests/                       # Focused API and empty-state tests
├── requirements.txt
├── .env.example
└── README.md
```

The frontend is served from the same FastAPI process. Dashboard values and
charts are loaded from persisted API results; empty databases remain empty.
```

When adding a future feature, create another folder under `pages/` using the same pattern: `index.html`, a descriptive CSS file, and a descriptive JavaScript file. Keep reusable functionality only in `assets/`.
