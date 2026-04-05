"""Fast cached dashboard overview endpoint."""
from __future__ import annotations

from collections import Counter
from time import monotonic

from fastapi import APIRouter, Query

from app.services.data_loader import load_data
from app.services.network_analysis import analyze_network
from app.services.timeseries_analysis import aggregate_timeseries
from app.services.topic_clustering import cluster_posts

router = APIRouter()

_CACHE_TTL_SECONDS = 120.0
_OVERVIEW_CACHE: dict[str, object] = {
    "built_at": 0.0,
    "payload": None,
}


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    force_refresh: bool = Query(False, description="Bypass the in-memory overview cache."),
):
    now = monotonic()
    cached_payload = _OVERVIEW_CACHE.get("payload")
    built_at = float(_OVERVIEW_CACHE.get("built_at", 0.0) or 0.0)

    if not force_refresh and cached_payload is not None and (now - built_at) < _CACHE_TTL_SECONDS:
        return {
            **cached_payload,
            "cache": {"hit": True, "stale": False, "ttl_seconds": int(_CACHE_TTL_SECONDS)},
        }

    try:
        payload = _build_overview_payload()
        _OVERVIEW_CACHE["payload"] = payload
        _OVERVIEW_CACHE["built_at"] = now
        return {
            **payload,
            "cache": {"hit": False, "stale": False, "ttl_seconds": int(_CACHE_TTL_SECONDS)},
        }
    except Exception as exc:
        if cached_payload is not None:
            return {
                **cached_payload,
                "cache": {
                    "hit": True,
                    "stale": True,
                    "ttl_seconds": int(_CACHE_TTL_SECONDS),
                    "message": f"Live refresh failed, serving stale cached overview: {exc}",
                },
            }
        raise


def warm_dashboard_overview_cache(force_refresh: bool = False) -> None:
    now = monotonic()
    cached_payload = _OVERVIEW_CACHE.get("payload")
    built_at = float(_OVERVIEW_CACHE.get("built_at", 0.0) or 0.0)
    if not force_refresh and cached_payload is not None and (now - built_at) < _CACHE_TTL_SECONDS:
        return

    payload = _build_overview_payload()
    _OVERVIEW_CACHE["payload"] = payload
    _OVERVIEW_CACHE["built_at"] = now


def _build_overview_payload() -> dict:
    df = load_data()
    stats = _build_stats_payload(df)
    timeseries = aggregate_timeseries(df, query="", granularity="week")
    platform_timeseries = aggregate_timeseries(df, query="", granularity="week", group_by="platform")
    topics = cluster_posts(requested_clusters=6).model_dump()
    network = analyze_network(
        query="",
        graph_type="account",
        scoring="pagerank",
        min_degree=1,
        remove_top_node=False,
    ).model_dump()

    return {
        "stats": stats,
        "timeseries": _aggregation_to_dict(timeseries),
        "platformTimeseries": _aggregation_to_dict(platform_timeseries),
        "topics": topics,
        "network": network,
    }


def _aggregation_to_dict(aggregation) -> dict:
    return {
        "query": aggregation.query,
        "granularity": aggregation.granularity,
        "group_by": aggregation.group_by,
        "data": [bucket.model_dump() for bucket in aggregation.data],
        "grouped": [series.model_dump() for series in aggregation.grouped],
        "total_posts": aggregation.total_posts,
        "date_range": aggregation.date_range,
        "summary": None,
        "summary_method": "dashboard-overview-skip-llm",
        "trend_shape": aggregation.trend_shape,
        "events": [],
        "event_comparison": None,
        "message": aggregation.message,
    }


def _build_stats_payload(df) -> dict:
    if df.empty:
        return {
            "total_posts": 0,
            "total_authors": 0,
            "date_range": None,
            "top_hashtags": [],
            "platforms": [],
            "top_authors": [],
        }

    all_tags = []
    for tags in df["hashtags"].dropna():
        if isinstance(tags, list):
            all_tags.extend(tags)
    tag_counts = Counter(all_tags)
    top_tags = [tag for tag, _ in tag_counts.most_common(20)]

    valid_dates = df["date"].dropna()
    date_range = None
    if len(valid_dates) > 0:
        date_range = {
            "start": str(valid_dates.min().date()),
            "end": str(valid_dates.max().date()),
        }

    platforms = []
    if df["platform"].notna().any():
        platform_counts = df["platform"].value_counts().head(10).to_dict()
        platforms = [{"name": k, "count": int(v)} for k, v in platform_counts.items()]

    top_authors = []
    if df["author"].notna().any():
        author_counts = (
            df.loc[df["author"].astype(str).str.strip().ne(""), "author"]
            .value_counts()
            .head(10)
            .to_dict()
        )
        top_authors = [{"name": k, "count": int(v)} for k, v in author_counts.items()]

    return {
        "total_posts": len(df),
        "total_authors": int(df["author"].nunique()),
        "date_range": date_range,
        "top_hashtags": top_tags,
        "platforms": platforms,
        "top_authors": top_authors,
    }
