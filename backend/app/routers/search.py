from __future__ import annotations

import re
from datetime import date

import pandas as pd
from fastapi import APIRouter, Query

from ..models.search_models import SearchResponse, SearchResultItem, SearchResultMetadata
from ..services.ai_summary import generate_related_queries
from ..services.data_loader import get_dataset_repository, load_data
from ..services.embeddings import get_provider
from ..services.retrieval import SemanticRetriever

router = APIRouter()

_retriever: SemanticRetriever | None = None
_indexed_post_ids: tuple[str, ...] = ()


def _get_retriever() -> SemanticRetriever:
    global _retriever
    if _retriever is None:
        _retriever = SemanticRetriever(get_provider())
    return _retriever


def _ensure_global_index(df: pd.DataFrame) -> SemanticRetriever:
    global _indexed_post_ids
    retriever = _get_retriever()
    if df.empty:
        _indexed_post_ids = ()
        retriever.index([])
        return retriever

    post_ids = tuple(str(value) for value in df["post_id"].tolist())
    if post_ids != _indexed_post_ids:
        retriever.index(df["text"].fillna("").astype(str).tolist())
        _indexed_post_ids = post_ids
    return retriever


def _generate_snippet(text: str, query: str, max_len: int = 200) -> str:
    if not text:
        return ""
    clean = text.replace("\n", " ").strip()

    words = [w for w in query.lower().split() if len(w) >= 2]
    best_pos = None
    for w in words:
        m = re.search(re.escape(w), clean, re.IGNORECASE)
        if m:
            best_pos = m.start()
            break

    if best_pos is not None:
        start = max(0, best_pos - max_len // 3)
    else:
        start = 0

    end = start + max_len
    snippet = clean[start:end]

    if start > 0:
        snippet = "…" + snippet
    if end < len(clean):
        snippet = snippet + "…"

    for w in words:
        snippet = re.sub(
            rf"({re.escape(w)})",
            r"**\1**",
            snippet,
            flags=re.IGNORECASE,
            count=3,
        )

    return snippet

def _apply_filters(
    df: pd.DataFrame,
    author: str | None,
    platform: str | None,
    date_from: date | None,
    date_to: date | None,
) -> pd.DataFrame:
    if author:
        df = df[df["author"].str.lower() == author.lower()]
    if platform:
        df = df[df["platform"].str.lower() == platform.lower()]
    if date_from:
        df = df[df["date"] >= pd.Timestamp(date_from, tz="UTC")]
    if date_to:
        df = df[df["date"] <= pd.Timestamp(date_to, tz="UTC")]
    return df

def _is_nat(val) -> bool:
    return pd.isna(val)


def _clean_optional_value(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    cleaned = str(val).strip()
    return cleaned or None


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search across posts",
    responses={
        200: {
            "description": "Search results",
            "content": {
                "application/json": {
                    "examples": {
                        "normal_search": {
                            "summary": "Normal search – 'protest'",
                            "value": {
                                "query": "protest",
                                "results": [
                                    {
                                        "text": "Protesting Safely – How to exercise your rights while staying protected...",
                                        "snippet": "**Protest**ing Safely – How to exercise your rights…",
                                        "author": "sharpteethx",
                                        "date": "2025-02-05",
                                        "url": "https://i.redd.it/gsci18aqawge1.png",
                                        "score": 0.7771,
                                        "hashtags": [],
                                        "platform": "r/50501",
                                        "metadata": {
                                            "post_id": "1abc123",
                                            "subreddit": "50501",
                                            "domain": "i.redd.it",
                                            "is_self_post": False,
                                            "comment_count": 42,
                                            "score_value": 188,
                                            "media_type": "image",
                                        },
                                    }
                                ],
                                "total": 1,
                                "message": None,
                                "related_queries": [
                                    "civil rights demonstrations",
                                    "activism and free speech",
                                    "protest safety tips",
                                ],
                                "retrieval_method": "embedding-cosine; source=backend/data/data.jsonl; indexed_records=8799",
                            },
                        },
                        "no_results": {
                            "summary": "No results – obscure query",
                            "value": {
                                "query": "zyxwvutsrqp quantum banana",
                                "results": [],
                                "total": 0,
                                "message": "No results matched your query. Try broadening your search.",
                                "related_queries": [],
                                "retrieval_method": "embedding-cosine; source=backend/data/data.jsonl; indexed_records=8799",
                            },
                        },
                        "short_query": {
                            "summary": "Very short query – single character",
                            "value": {
                                "query": "a",
                                "results": [],
                                "total": 0,
                                "message": "Query too short. Please enter at least 2 characters.",
                                "related_queries": [],
                                "retrieval_method": "not-run",
                            },
                        },
                        "non_english_query": {
                            "summary": "Non-English query – Chinese '抗议' (protest)",
                            "value": {
                                "query": "抗议",
                                "results": [
                                    {
                                        "text": "The Great American Protest marches continued across cities...",
                                        "snippet": "The Great American Protest marches continued across cities…",
                                        "author": "transcendent167",
                                        "date": "2025-02-03",
                                        "url": "https://reddit.com/r/50501/...",
                                        "score": 0.4823,
                                        "hashtags": [],
                                        "platform": "r/50501",
                                        "metadata": {
                                            "post_id": "1def456",
                                            "subreddit": "50501",
                                            "domain": "reddit.com",
                                            "is_self_post": True,
                                            "comment_count": 18,
                                            "score_value": 91,
                                            "media_type": "self",
                                        },
                                    }
                                ],
                                "total": 1,
                                "message": None,
                                "related_queries": [],
                                "retrieval_method": "embedding-cosine; source=backend/data/data.jsonl; indexed_records=8799",
                            },
                        },
                    }
                }
            },
        }
    },
)
async def search_posts(
    q: str = Query("", description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    author: str | None = Query(None, description="Filter by author"),
    platform: str | None = Query(None, description="Filter by platform"),
    date_from: date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="End date (YYYY-MM-DD)"),
) -> SearchResponse:
    q = q.strip()

    if not q:
        return SearchResponse(
            query="",
            results=[],
            total=0,
            message="Please enter a search query to find relevant posts.",
            retrieval_method="not-run",
        )

    if len(q) < 2:
        return SearchResponse(
            query=q,
            results=[],
            total=0,
            message="Query too short. Please enter at least 2 characters.",
            retrieval_method="not-run",
        )

    repo = get_dataset_repository()
    df = load_data()
    if df.empty:
        return SearchResponse(
            query=q,
            results=[],
            total=0,
            message="No dataset loaded from backend/data/data.jsonl.",
            retrieval_method="not-run",
        )

    filtered = _apply_filters(df, author, platform, date_from, date_to)
    if filtered.empty:
        return SearchResponse(
            query=q,
            results=[],
            total=0,
            message="No posts match the applied filters.",
            retrieval_method="not-run",
        )

    retrieval_method = "embedding-cosine"
    if len(filtered) == len(df):
        retriever = _ensure_global_index(df)
        hits = retriever.search(q, top_k=limit, threshold=0.05)
        retrieval_method = retriever.retrieval_method
    else:
        retriever = SemanticRetriever(get_provider())
        texts = filtered["text"].fillna("").astype(str).tolist()
        retriever.index(texts)
        hits = retriever.search(q, top_k=limit, threshold=0.05)
        retrieval_method = retriever.retrieval_method

    results: list[SearchResultItem] = []
    for hit in hits:
        row = filtered.iloc[hit.index]
        raw_text = str(row["text"])

        results.append(
            SearchResultItem(
                text=raw_text[:500],
                snippet=_generate_snippet(raw_text, q),
                author=row.get("author"),
                date=(
                    str(row["date"].date())
                    if row.get("date") is not None and not _is_nat(row["date"])
                    else None
                ),
                url=row.get("url"),
                score=hit.score,
                hashtags=(
                    row.get("hashtags")
                    if isinstance(row.get("hashtags"), list)
                    else []
                ),
                platform=row.get("platform"),
                metadata=SearchResultMetadata(
                    post_id=_clean_optional_value(row.get("post_id")),
                    subreddit=_clean_optional_value(row.get("subreddit_name")),
                    domain=_clean_optional_value(row.get("domain")),
                    is_self_post=bool(row.get("is_self_post")) if row.get("is_self_post") is not None else None,
                    comment_count=(
                        int(row.get("comment_count"))
                        if row.get("comment_count") is not None and not _is_nat(row.get("comment_count"))
                        else None
                    ),
                    score_value=(
                        int(row.get("score"))
                        if row.get("score") is not None and not _is_nat(row.get("score"))
                        else None
                    ),
                    media_type=_clean_optional_value(row.get("media_type")),
                ),
            )
        )

    related = await generate_related_queries(q)

    message = None
    if not results:
        message = "No results matched your query. Try broadening your search."
        if len(filtered) < 3:
            message = "The filtered dataset is very small, so semantic search may be sparse. Try broader filters."
        elif len(filtered) < 25:
            message = "The filtered dataset is small or sparse, so results may be limited."

    if retrieval_method.startswith("token-overlap"):
        retrieval_method = f"{retrieval_method} (small/sparse corpus fallback)"
    elif retrieval_method.endswith("fallback"):
        retrieval_method = f"{retrieval_method} (embedding results were too weak)"

    if not related and len(results) and q:
        related = _fallback_related_queries(q, results[:3])

    return SearchResponse(
        query=q,
        results=results,
        total=len(results),
        message=message,
        related_queries=related,
        retrieval_method=(
            f"{retrieval_method}; source=backend/data/data.jsonl; indexed_records={repo.stats.valid_records}"
        ),
    )


def _fallback_related_queries(query: str, results: list[SearchResultItem]) -> list[str]:
    seeds: list[str] = []
    for item in results:
        subreddit = item.metadata.subreddit
        if subreddit:
            seeds.append(subreddit)
        for tag in item.hashtags[:2]:
            seeds.append(f"#{tag}")
        if item.metadata.domain:
            seeds.append(item.metadata.domain)

    suggestions: list[str] = []
    seen = {query.lower()}
    for seed in seeds:
        candidate = f"{query} {seed}".strip()
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        suggestions.append(candidate)
        if len(suggestions) == 3:
            break
    return suggestions
