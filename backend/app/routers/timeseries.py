"""
Time-series analytics endpoint – Post volume over time.

Features:
  - Configurable time bucket: hour, day, week
  - Optional grouping by platform, author, or hashtag
  - GenAI summary derived from the actual data (never hardcoded)
  - Rule-based fallback summary with trend/peak/sparsity detection
  - Edge-case handling: empty data, sparse periods, flat trends
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from fastapi import APIRouter, Query

from ._cache_utils import ResponseCache
from ..models.events_models import EventComparison
from ..models.timeseries_models import (
    TimeseriesBucket,
    TimeseriesResponse,
)
from ..services.ai_summary import (
    generate_timeseries_summary,
)
from ..services.data_loader import load_data
from ..services.events_loader import load_events
from ..services.timeseries_analysis import FREQ_MAP, VALID_GROUPS, aggregate_timeseries

router = APIRouter()
_TIMESERIES_CACHE = ResponseCache(ttl_seconds=90.0)

@router.get(
    "/timeseries",
    response_model=TimeseriesResponse,
    summary="Post volume over time with optional grouping and AI summary",
)
async def get_timeseries(
    q: str = Query("", description="Optional text filter"),
    granularity: str = Query("day", description="hour | day | week"),
    group_by: Optional[str] = Query(
        None, description="Optional grouping: platform | author | hashtag | topic"
    ),
    event_id: Optional[str] = Query(None, description="Optional offline event id for overlay/comparison"),
) -> TimeseriesResponse:
    q = q.strip()
    granularity = granularity.lower()
    if granularity not in FREQ_MAP:
        granularity = "day"
    if group_by and group_by not in VALID_GROUPS:
        group_by = None

    cache_key = f"q={q}|granularity={granularity}|group_by={group_by or ''}|event_id={event_id or ''}"
    cached = _TIMESERIES_CACHE.get(cache_key)
    if cached is not None:
        return cached

    df = load_data()
    aggregation = aggregate_timeseries(
        df,
        query=q,
        granularity=granularity,
        group_by=group_by,
    )

    date_start, date_end = _response_date_bounds(aggregation)
    events = _events_in_range(date_start, date_end) if date_start is not None and date_end is not None else []
    event_comparison = _build_event_comparison(aggregation.data, events, event_id)
    selected_event = next((item for item in events if item.id == event_id), None) if event_id else None

    summary = None
    summary_method = None
    if aggregation.data or aggregation.grouped_context:
        summary, summary_method = await generate_timeseries_summary(
            buckets=[bucket.model_dump() for bucket in aggregation.data],
            query=aggregation.query,
            granularity=aggregation.granularity,
            total_posts=aggregation.total_posts,
            group_by=aggregation.group_by,
            grouped=aggregation.grouped_context[:10] if aggregation.grouped_context else None,
            selected_event=selected_event,
            event_comparison=event_comparison,
        )

    response = TimeseriesResponse(
        query=aggregation.query,
        granularity=aggregation.granularity,
        group_by=aggregation.group_by,
        data=aggregation.data,
        grouped=aggregation.grouped,
        total_posts=aggregation.total_posts,
        date_range=aggregation.date_range,
        summary=summary,
        summary_method=summary_method,
        trend_shape=aggregation.trend_shape,
        events=events,
        event_comparison=event_comparison,
        message=aggregation.message,
    )
    _TIMESERIES_CACHE.set(cache_key, response)
    return response


def _response_date_bounds(aggregation) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    labels: list[str] = []
    if aggregation.data:
        labels = [bucket.date for bucket in aggregation.data]
    elif aggregation.grouped_context:
        for series in aggregation.grouped_context:
            labels.extend(bucket["date"] for bucket in series.get("buckets", []))

    if not labels:
        return None, None

    parsed: list[pd.Timestamp] = []
    for label in labels:
        try:
            parsed.append(pd.Timestamp(label, tz="UTC"))
        except Exception:
            continue
    if not parsed:
        return None, None
    return min(parsed), max(parsed)


def _events_in_range(date_start: pd.Timestamp, date_end: pd.Timestamp):
    results = []
    if date_start is None or date_end is None:
        return results
    for event in load_events():
        try:
            event_date = pd.Timestamp(event.date, tz="UTC")
        except Exception:
            continue
        if date_start <= event_date <= date_end:
            results.append(event)
    return results


def _build_event_comparison(
    buckets: list[TimeseriesBucket],
    events,
    event_id: str | None,
) -> EventComparison | None:
    if not event_id or not buckets:
        return None

    event = next((item for item in events if item.id == event_id), None)
    if event is None:
        return None

    event_index = next((idx for idx, bucket in enumerate(buckets) if str(bucket.date).startswith(event.date)), None)
    if event_index is None:
        return None

    window = 3
    before = buckets[max(0, event_index - window):event_index]
    after = buckets[event_index + 1:event_index + 1 + window]
    before_total = sum(bucket.count for bucket in before)
    after_total = sum(bucket.count for bucket in after)
    delta = after_total - before_total
    ratio = (delta / before_total) if before_total > 0 else None

    return EventComparison(
        event_id=event.id,
        event_title=event.title,
        before_total=before_total,
        after_total=after_total,
        delta=delta,
        change_ratio=ratio,
        window_buckets=window,
    )
