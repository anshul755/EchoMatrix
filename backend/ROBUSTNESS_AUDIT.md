# Backend Robustness Audit

This document records the main failure modes considered for the EchoMatrix backend, the safeguards already implemented, and the checks that should be run before release.

It is intended as a practical engineering audit, not a theoretical checklist.

## Scope

The audit covers the FastAPI backend in `backend/app` and the JSONL-driven data pipeline used by:

- semantic search
- time-series analysis
- topic clustering
- network analysis
- dashboard aggregation
- events overlay support
- Gemini summary generation

## Core Risk Areas

### 1. Dataset Ingestion Risks

Potential issues:

- malformed JSONL rows
- empty lines
- unexpected row shapes
- missing `kind` or `data`
- missing `id`
- missing `created_utc`
- empty `title` and `selftext`
- invalid URLs
- mixed optional field types such as `edited`

Current safeguards:

- line-by-line JSONL parsing
- malformed rows are skipped instead of crashing the loader
- invalid shapes are tracked as loader issues
- rows with no usable text are skipped
- missing authors and subreddits fall back to placeholders
- invalid timestamps are tolerated and normalized safely
- canonical URL derivation falls back safely
- loader repository caches normalized output for reuse

Relevant files:

- [app/services/data_loader.py](./app/services/data_loader.py)
- [app/core/config.py](./app/core/config.py)

## 2. Search And Embedding Risks

Potential issues:

- embedding model unavailable
- tiny or sparse corpora
- empty search query
- very short query
- non-English query
- stale embedding cache
- invalid metadata values in results

Current safeguards:

- sentence-transformer path with fallback behavior
- safe handling for weak or tiny corpora
- friendly API response for empty and short queries
- metadata normalization in API responses
- retrieval stays operational even if the ideal semantic path is degraded

Relevant files:

- [app/services/embeddings.py](./app/services/embeddings.py)
- [app/services/retrieval.py](./app/services/retrieval.py)
- [app/routers/search.py](./app/routers/search.py)

## 3. Time-Series Risks

Potential issues:

- regex-like user query crashing string filtering
- sparse buckets
- flat signal
- tiny result set
- grouped series inconsistency
- event overlay missing or invalid
- summary generation failure

Current safeguards:

- literal query handling instead of unsafe regex behavior
- explicit empty, tiny, flat, and sparse fallbacks
- grouped output remains chart-ready
- offline event overlay is optional
- event comparison is only returned when valid
- Gemini failure falls back to rule-based summaries

Relevant files:

- [app/services/timeseries_analysis.py](./app/services/timeseries_analysis.py)
- [app/services/ai_summary.py](./app/services/ai_summary.py)
- [app/routers/timeseries.py](./app/routers/timeseries.py)
- [app/routers/events.py](./app/routers/events.py)

## 4. Topic Clustering Risks

Potential issues:

- no usable corpus
- one-record corpus
- extreme `n_clusters`
- duplicate or repetitive text
- poor label generation on tiny clusters
- projector export becoming too large

Current safeguards:

- safe empty and singleton handling
- cluster count clipping and reduction against usable corpus size
- deterministic `KMeans` settings for stable output
- representative post selection avoids unstable sampling
- projector export is capped for responsiveness

Relevant files:

- [app/services/topic_clustering.py](./app/services/topic_clustering.py)
- [app/services/projector_export.py](./app/services/projector_export.py)
- [app/routers/topics.py](./app/routers/topics.py)

## 5. Network Analysis Risks

Potential issues:

- malformed URLs breaking graph construction
- sparse graph results
- disconnected graphs
- missing relationship types in the dataset
- invalid filters
- expensive graph recomputation

Current safeguards:

- safe URL normalization fallback
- graph metadata reports disconnected or sparse states
- inferred relationships are surfaced in response metadata
- optional resilience analysis is isolated and explicit
- endpoint responses are cached for repeated access

Relevant files:

- [app/services/network_analysis.py](./app/services/network_analysis.py)
- [app/routers/network.py](./app/routers/network.py)

## 6. Gemini Integration Risks

Potential issues:

- no API key configured
- quota exhaustion
- rate limiting
- key-specific failure
- partial Gemini responses with non-text parts
- latency spikes

Current safeguards:

- multi-key rotation through `GEMINI_API_KEYS`
- retry/rotation on quota, auth, rate-limit, and service-style failures
- text extraction from Gemini response parts only
- safe fallback summaries when Gemini is unavailable

Relevant files:

- [app/services/ai_summary.py](./app/services/ai_summary.py)
- [app/core/config.py](./app/core/config.py)

## 7. Performance Risks

Potential issues:

- expensive first request after server start
- repeated heavy dashboard loads
- repeated clustering or network requests
- large JSON responses

Current safeguards:

- dataset cache
- embedding warm-up on startup
- dashboard overview warm-up on startup
- in-memory endpoint caches for heavy routes
- gzip compression enabled in FastAPI

Relevant files:

- [app/main.py](./app/main.py)
- [app/routers/dashboard.py](./app/routers/dashboard.py)
- [app/routers/_cache_utils.py](./app/routers/_cache_utils.py)

## Recommended Verification Checklist

Run these before release or after major backend changes.

### Loader Checks

- start the backend with a valid `data.jsonl`
- verify `/health` returns `status: ok`
- verify malformed rows do not stop startup
- verify `POST /dev/reload-data` completes successfully

### Search Checks

- `/api/search?q=reading circle`
- `/api/search?q=a`
- `/api/search?q=抗议`
- verify empty query returns a controlled response

### Time-Series Checks

- `/api/timeseries?query=trump&bucket=week`
- grouped request with `group_by=platform`
- request with an event selected
- query containing regex-like characters such as `[` or `+`

### Topics Checks

- `/api/topics?n_clusters=1`
- `/api/topics?n_clusters=8`
- `/api/topics?n_clusters=99`
- `/api/topics/projector?n_clusters=8`

### Network Checks

- `/api/network?graph_type=account`
- `/api/network?graph_type=topic`
- `/api/network?graph_type=account&remove_top_node=true`
- verify sparse/disconnected responses remain valid

### Dashboard Checks

- `/api/dashboard/overview`
- verify repeat requests are faster because of cache reuse

### Gemini Checks

- verify summaries work when keys are valid
- verify fallback summaries work when Gemini is unavailable
- verify multi-key configuration loads correctly

## Residual Risks

These are acceptable current limitations, but they should stay visible:

- first request after cold start can still be slower than warm requests
- sentence-transformer quality depends on runtime availability and model load state
- inferred network relationships are only as strong as the dataset allows
- AI summary quality depends on Gemini availability and response quality

## Conclusion

The backend is designed to fail soft rather than fail hard. The main pattern across the codebase is:

- skip bad data
- return explicit messages
- keep endpoints responsive through caching
- preserve a fallback path when ideal ML or LLM behavior is unavailable

That is the right operational posture for a data-heavy exploratory dashboard built on imperfect real-world input.
