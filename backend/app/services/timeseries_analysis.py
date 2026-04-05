"""
Aggregation helpers for time-series analytics over the normalized dataset.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from app.models.timeseries_models import GroupedSeries, TimeseriesBucket

BucketSize = Literal["hour", "day", "week"]
GroupBy = Literal["platform", "author", "hashtag", "topic"]

FREQ_MAP: dict[BucketSize, str] = {"hour": "h", "day": "D", "week": "W"}
VALID_GROUPS: set[str] = {"platform", "author", "hashtag", "topic"}


@dataclass(slots=True)
class TimeseriesAggregation:
    query: str
    granularity: BucketSize
    group_by: str | None
    total_posts: int
    date_range: str | None
    data: list[TimeseriesBucket]
    grouped: list[GroupedSeries]
    grouped_context: list[dict]
    message: str | None
    trend_shape: str


def aggregate_timeseries(
    frame: pd.DataFrame,
    *,
    query: str = "",
    granularity: str = "day",
    group_by: str | None = None,
) -> TimeseriesAggregation:
    normalized_granularity: BucketSize = granularity if granularity in FREQ_MAP else "day"
    normalized_group_by = group_by if group_by in VALID_GROUPS else None

    if frame.empty:
        return TimeseriesAggregation(
            query=query,
            granularity=normalized_granularity,
            group_by=normalized_group_by,
            total_posts=0,
            date_range=None,
            data=[],
            grouped=[],
            grouped_context=[],
            message="No dataset loaded from backend/data/data.jsonl.",
            trend_shape="empty",
        )

    working = frame.copy()
    if query.strip():
        mask = working["text"].fillna("").str.contains(
            query.strip(),
            case=False,
            na=False,
            regex=False,
        )
        working = working[mask]

    if working.empty:
        return TimeseriesAggregation(
            query=query,
            granularity=normalized_granularity,
            group_by=normalized_group_by,
            total_posts=0,
            date_range=None,
            data=[],
            grouped=[],
            grouped_context=[],
            message=f'No posts matched the filter "{query.strip()}".',
            trend_shape="empty",
        )

    working = working.dropna(subset=["date"]).copy()
    if working.empty:
        return TimeseriesAggregation(
            query=query,
            granularity=normalized_granularity,
            group_by=normalized_group_by,
            total_posts=0,
            date_range=None,
            data=[],
            grouped=[],
            grouped_context=[],
            message="No posts with valid dates in the dataset.",
            trend_shape="empty",
        )

    working["topic"] = _topic_series(working)
    total_posts = len(working)
    working = working.set_index("date").sort_index()
    date_range = (
        f"{working.index.min().strftime('%Y-%m-%d')} to "
        f"{working.index.max().strftime('%Y-%m-%d')}"
    )

    if normalized_group_by:
        grouped_frame = _prepare_group_frame(working, normalized_group_by)
        if grouped_frame is None or normalized_group_by not in grouped_frame.columns:
            return TimeseriesAggregation(
                query=query,
                granularity=normalized_granularity,
                group_by=normalized_group_by,
                total_posts=total_posts,
                date_range=date_range,
                data=[],
                grouped=[],
                grouped_context=[],
                message=f'Column "{normalized_group_by}" not available in the dataset.',
                trend_shape="empty",
            )

        grouped_series: list[GroupedSeries] = []
        grouped_context: list[dict] = []
        for name, grp in grouped_frame.groupby(normalized_group_by):
            group_name = str(name).strip() or "(unknown)"
            buckets = _resample_counts(grp[[]], FREQ_MAP[normalized_granularity])
            if not buckets:
                continue
            grouped_series.append(GroupedSeries(group=group_name, buckets=buckets))
            grouped_context.append(
                {"group": group_name, "buckets": [bucket.model_dump() for bucket in buckets]}
            )

        grouped_series.sort(key=lambda item: sum(bucket.count for bucket in item.buckets), reverse=True)
        grouped_context.sort(key=lambda item: sum(bucket["count"] for bucket in item["buckets"]), reverse=True)
        return TimeseriesAggregation(
            query=query,
            granularity=normalized_granularity,
            group_by=normalized_group_by,
            total_posts=total_posts,
            date_range=date_range,
            data=[],
            grouped=grouped_series[:20],
            grouped_context=grouped_context[:20],
            message=None if grouped_series else "No grouped time-series data could be built from the selected filters.",
            trend_shape=_grouped_shape(grouped_context),
        )

    buckets = _resample_counts(working[[]], FREQ_MAP[normalized_granularity])
    return TimeseriesAggregation(
        query=query,
        granularity=normalized_granularity,
        group_by=None,
        total_posts=total_posts,
        date_range=date_range,
        data=buckets,
        grouped=[],
        grouped_context=[],
        message=None if buckets else "No time buckets were produced from the selected filters.",
        trend_shape=_trend_shape([bucket.model_dump() for bucket in buckets], total_posts),
    )


def _prepare_group_frame(frame: pd.DataFrame, group_by: str) -> pd.DataFrame | None:
    if group_by == "hashtag":
        exploded = frame.reset_index().copy()
        exploded["hashtag"] = exploded["hashtags"].apply(
            lambda values: values if isinstance(values, list) and values else ["(none)"]
        )
        return exploded.explode("hashtag").set_index("date").sort_index()
    return frame


def _resample_counts(frame: pd.DataFrame, freq: str) -> list[TimeseriesBucket]:
    series = frame.resample(freq).size().reset_index(name="count")
    fmt = "%Y-%m-%dT%H:%M" if freq == "h" else "%Y-%m-%d"
    series["date"] = series["date"].dt.strftime(fmt)
    return [TimeseriesBucket(date=row["date"], count=int(row["count"])) for _, row in series.iterrows()]


def _topic_series(frame: pd.DataFrame) -> pd.Series:
    if "link_flair_text" not in frame.columns:
        return pd.Series(["(unlabeled)"] * len(frame), index=frame.index)
    return (
        frame["link_flair_text"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", "(unlabeled)")
    )


def _trend_shape(buckets: list[dict], total_posts: int) -> str:
    if not buckets or total_posts == 0:
        return "empty"
    counts = [bucket["count"] for bucket in buckets]
    if total_posts <= 3 or len(buckets) <= 2:
        return "tiny"
    if len(set(counts)) <= 1:
        return "flat"
    zero_ratio = counts.count(0) / max(len(counts), 1)
    if zero_ratio >= 0.6:
        return "sparse"
    return "varied"


def _grouped_shape(grouped: list[dict]) -> str:
    if not grouped:
        return "empty"
    if len(grouped) <= 2:
        return "tiny"
    totals = [sum(bucket["count"] for bucket in item["buckets"]) for item in grouped]
    if len(set(totals)) <= 1:
        return "flat"
    return "varied"
