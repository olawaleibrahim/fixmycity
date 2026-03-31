# FixMyCity — Urban Insight Platform

AI-powered platform that automatically aggregates and analyses urban hazards and housing conditions from open data sources.

## Week 1 MVP — What's built

- **Ingestion (no API keys)** — FixMyStreet civic reports, EA Flood Monitoring, BBC/Guardian RSS feeds
- **NLP pipeline** — keyword-based classification, spaCy NER location extraction, Nominatim geocoding
- **Severity scoring** — engagement + confidence + recency decay formula
- **FastAPI backend** — `/events`, `/map/events`, `/map/stats` endpoints
- **Leaflet map frontend** — Next.js + Tailwind, interactive map with colour-coded pins, time + type filters

### Data sources

| Source | What it provides | API key? |
|---|---|---|
| [FixMyStreet](https://www.fixmystreet.com) | UK civic issue reports — potholes, litter, broken lights, graffiti | None |
| [EA Flood Monitoring](https://environment.data.gov.uk/flood-monitoring) | Real-time flood alerts across England | None |
| BBC / Guardian RSS | Local news with urban hazard context | None |

---

## Quick start

### 1. Environment

```bash
cp .env.example .env
# Set NOMINATIM_USER_AGENT to your email address (required by OpenStreetMap ToS)
```

### 2. Start the database

```bash
docker-compose up db -d
```

### 3. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000
API docs at http://localhost:8000/docs

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000

### Or: run everything with Docker

```bash
docker-compose up --build
```

---

## API reference

| Endpoint | Description |
|---|---|
| `GET /events/` | List hazard events (filters: `hazard_type`, `time_range`, `min_severity`) |
| `GET /map/events` | GeoJSON FeatureCollection for map layer |
| `GET /map/stats` | Event counts by hazard type |
| `POST /admin/trigger-pipeline` | Manually trigger ingestion + processing |
| `GET /health` | Health check |

---

## Project structure

```
fixmycity/
├── backend/
│   └── app/
│       ├── ingestion/      # FixMyStreet, EA Flood API, RSS feeds
│       ├── processing/nlp/ # Classifier, NER, geocoder, pipeline
│       ├── scoring/        # Severity formula
│       ├── api/            # FastAPI routes
│       ├── models/         # SQLAlchemy DB models
│       └── tasks/          # APScheduler (hourly pipeline)
└── frontend/
    ├── app/                # Next.js App Router pages
    ├── components/         # HazardMap, Sidebar
    ├── lib/                # API client
    └── types/              # TypeScript types
```

## Roadmap

- **Week 2** — CV model (YOLO) for image classification, severity upgrade with CV score, dashboard
- **Week 3** — Property listing scraper, rental analyser (CV + NLP), UI polish
