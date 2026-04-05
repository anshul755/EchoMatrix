# EchoMatrix Backend

FastAPI backend for the EchoMatrix investigative narrative dashboard.

This service ingests a Reddit-style JSONL dataset, normalizes it into a usable internal record shape, builds cached analytical views, and exposes API endpoints for search, trends, topic clustering, network analysis, dashboard aggregation, and event overlays.

## Overview

The backend is responsible for:

- loading and normalizing `backend/data/data.jsonl`
- caching processed dataset state for faster startup and repeated reads
- generating embeddings for semantic retrieval and topic clustering
- serving search, trends, topics, network, stats, events, and dashboard endpoints
- producing AI summaries and related-query suggestions through Gemini with multi-key rotation
- exposing health and dev reload endpoints

## Stack

| Layer | Tools |
| --- | --- |
| API framework | FastAPI |
| ASGI server | Uvicorn |
| Data handling | pandas, numpy |
| ML / retrieval | scikit-learn, sentence-transformers |
| Graph analysis | networkx |
| Dimensionality reduction | umap-learn |
| LLM integration | google-genai |
| Config loading | python-dotenv |

## Requirements

- Python 3.11+ recommended
- pip or a virtual environment tool
- A local dataset file at `backend/data/data.jsonl`
- Gemini API key access if you want AI summaries instead of rule-based fallbacks

## Quick Start

1. Create and activate a virtual environment:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create a local environment file:

```powershell
Copy-Item .env.example .env
```

4. Set your local environment values in `.env`

Minimum example:

```env
GEMINI_API_KEYS=your_key_1,your_key_2,your_key_3,your_key_4,your_key_5
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

5. Start the API:

```powershell
uvicorn app.main:app --reload
```

Default local API URL:

```text
http://localhost:8000
```

## API Base and Health

Root endpoint:

```text
GET /
```

Health check:

```text
GET /health
```

Expected local health URL:

```text
http://localhost:8000/health
```

## Environment Variables

### Gemini keys

You can configure Gemini in any of these forms:

```env
GEMINI_API_KEYS=key1,key2,key3,key4,key5
```

or:

```env
GEMINI_API_KEY=key1
```

or:

```env
GEMINI_API_KEY_1=key1
GEMINI_API_KEY_2=key2
GEMINI_API_KEY_3=key3
GEMINI_API_KEY_4=key4
GEMINI_API_KEY_5=key5
```

The backend deduplicates keys and rotates automatically when Gemini returns quota, rate-limit, auth, or service-availability style failures.

### Allowed origins

```env
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,https://your-frontend-domain.vercel.app
```

## Project Structure

```text
backend/
├── app/
│   ├── core/           # settings and configuration
│   ├── models/         # response and request models
│   ├── routers/        # FastAPI route modules
│   ├── services/       # data loading, embeddings, clustering, retrieval, graph logic
│   └── main.py         # FastAPI app entrypoint
├── data/
│   ├── data.jsonl      # source dataset
│   └── .cache/         # generated backend caches
├── .env.example
├── requirements.txt
└── README.md
```

## Data Pipeline

The backend expects a JSONL corpus in:

- `backend/data/data.jsonl`

The loader:

- reads the file line by line
- handles malformed rows safely
- unwraps Reddit `kind=t3` / `data` objects
- skips unusable records
- normalizes fields into a canonical internal structure
- caches the processed repository in `backend/data/.cache/`

Normalized records include fields such as:

- `text`
- `author`
- `date`
- `url`
- `hashtags`
- `platform`
- `post_id`
- `title`
- `body_text`
- `full_text`
- `canonical_url`
- `domain`
- `media_type`

## Service Modules

Key service files:

- [app/services/data_loader.py](./app/services/data_loader.py)
- [app/services/embeddings.py](./app/services/embeddings.py)
- [app/services/retrieval.py](./app/services/retrieval.py)
- [app/services/timeseries_analysis.py](./app/services/timeseries_analysis.py)
- [app/services/topic_clustering.py](./app/services/topic_clustering.py)
- [app/services/network_analysis.py](./app/services/network_analysis.py)
- [app/services/projector_export.py](./app/services/projector_export.py)
- [app/services/events_loader.py](./app/services/events_loader.py)
- [app/services/ai_summary.py](./app/services/ai_summary.py)

## API Surface

Primary route modules:

- [app/routers/search.py](./app/routers/search.py)
- [app/routers/timeseries.py](./app/routers/timeseries.py)
- [app/routers/topics.py](./app/routers/topics.py)
- [app/routers/network.py](./app/routers/network.py)
- [app/routers/stats.py](./app/routers/stats.py)
- [app/routers/events.py](./app/routers/events.py)
- [app/routers/dashboard.py](./app/routers/dashboard.py)

Main endpoints:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/search` | Semantic search and ranked retrieval |
| `GET /api/timeseries` | Time-series buckets, grouped trends, event overlays |
| `GET /api/topics` | Topic clustering output |
| `GET /api/topics/projector` | Embedding export metadata for projector use |
| `GET /api/network` | Network analysis and resilience views |
| `GET /api/stats` | Dataset-level summary metrics |
| `GET /api/events` | Offline event overlay dataset |
| `GET /api/dashboard/overview` | Aggregated overview payload for the frontend dashboard |
| `POST /dev/reload-data` | Manual data reload for local development |

## Caching and Performance

The backend includes multiple layers of speed improvements:

- dataset repository caching
- serialized loader cache in `backend/data/.cache/`
- embedding warm-up on startup
- dashboard overview warm-up on startup
- short-lived in-memory caches for heavy endpoints
- gzip compression for larger JSON payloads

Startup warm-up currently prepares:

- dataset state
- embeddings
- dashboard overview cache

## AI Summary Behavior

Gemini is used for:

- time-series summaries
- related query suggestions

Implementation details:

- uses `google-genai`
- rotates across multiple Gemini keys when needed
- extracts text safely from Gemini response parts
- falls back to rule-based summaries when Gemini is unavailable

If no valid Gemini key is configured, the API still works. Only the AI-generated summary layer falls back.

## Search and Embeddings

Semantic search and clustering rely on:

- sentence-transformer embeddings when available
- cached provider state for repeat requests
- fallback logic for weak or tiny corpora

This means the backend remains operational even if the full embedding path is degraded, though quality may be lower in fallback mode.

## Topic Clustering

Topic clustering uses:

- embedding vectors
- deterministic `KMeans`
- TF-IDF keywords for labels
- representative posts near cluster centroids

It also supports:

- tunable `n_clusters`
- safe handling for tiny datasets
- capped projector export for embedding exploration

## Network Analysis

The network layer builds graph views from dataset-derived relationships, including:

- account graphs
- hashtag graphs
- URL graphs
- post graphs
- topic graphs

It exposes:

- PageRank
- betweenness
- community detection
- disconnected-graph signaling
- optional top-node removal resilience analysis

## Development Workflow

Common local commands:

Run the server:

```powershell
uvicorn app.main:app --reload
```

Test health:

```text
http://localhost:8000/health
```

Reload dataset during local development:

```text
POST http://localhost:8000/dev/reload-data
```

## Production Notes

- Keep the dataset available at the configured data path
- Set `ALLOWED_ORIGINS` to the real frontend domain
- Provide Gemini keys through environment variables, not source code
- Use the frontend `VITE_API_BASE_URL` to point at this backend’s `/api` root
- Startup warm-up improves first-request latency after boot

## Verification

Recommended backend verification after setup:

1. Start the server
2. Open `/health`
3. Test key endpoints:
   - `/api/dashboard/overview`
   - `/api/search?q=reading circle`
   - `/api/timeseries?query=trump&bucket=week`
   - `/api/topics?n_clusters=8`
   - `/api/network?graph_type=account`

## Troubleshooting

### `/health` works but AI summaries are missing

This usually means Gemini keys are missing, invalid, or rate-limited. The backend should still return fallback summaries.

### Search or topic clustering is slower on first request

The first request can include model warm-up costs if the process was freshly started.

### Frontend cannot talk to the backend

Check:

- the API is running
- `ALLOWED_ORIGINS` includes the frontend origin
- the frontend points to the backend `/api` base URL

### Dataset changes are not reflected

Use:

```text
POST /dev/reload-data
```

or restart the backend.

## Security Notes

- Do not commit `.env`
- Keep Gemini keys only in environment variables
- `.gitignore` already excludes local secrets and cache files
