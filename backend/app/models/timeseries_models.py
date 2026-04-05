"""
Pydantic models for the time-series analytics endpoint.

Provides a chart-ready response contract with:
  - Configurable time buckets (hour / day / week)
  - Optional grouping by platform, author, hashtag, or topic
  - GenAI-generated summary derived from the actual data
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field
from .events_models import EventComparison, EventItem


# ── Request ─────────────────────────────────────────────────────

BucketSize = Literal["hour", "day", "week"]
GroupBy = Literal["platform", "author", "hashtag", "topic"]


# ── Response items ──────────────────────────────────────────────

class TimeseriesBucket(BaseModel):
    """A single time bucket with post count."""

    date: str = Field(..., description="Bucket label (ISO date or datetime string).")
    count: int = Field(..., description="Number of posts in this bucket.")


class GroupedSeries(BaseModel):
    """One series within a grouped breakdown."""

    group: str = Field(..., description="Group value (e.g. platform name, author).")
    buckets: list[TimeseriesBucket] = Field(
        default_factory=list, description="Time buckets for this group."
    )


class TimeseriesResponse(BaseModel):
    """Top-level response for the time-series analytics endpoint.

    When `group_by` is set, `grouped` contains per-group breakdowns.
    Otherwise, `data` contains the single aggregated series.
    The `summary` field contains a GenAI-generated or fallback plain-language
    description derived from the actual data — never hardcoded boilerplate.
    """

    query: str = Field("", description="Echo of the filter query.")
    granularity: BucketSize = Field("day", description="Time bucket size used.")
    group_by: Optional[GroupBy] = Field(None, description="Grouping dimension, if any.")
    data: list[TimeseriesBucket] = Field(
        default_factory=list,
        description="Aggregated time-series (populated when group_by is None).",
    )
    grouped: list[GroupedSeries] = Field(
        default_factory=list,
        description="Per-group time-series (populated when group_by is set).",
    )
    total_posts: int = Field(0, description="Total posts in the result set.")
    date_range: Optional[str] = Field(
        None, description="Human-readable date range, e.g. '2025-01-15 to 2025-02-12'."
    )
    summary: Optional[str] = Field(
        None,
        description="Plain-language summary of the trend, derived from the returned data.",
    )
    summary_method: Optional[str] = Field(
        None,
        description="How the summary was generated, e.g. LLM or rule-based fallback.",
    )
    trend_shape: Optional[str] = Field(
        None,
        description="Quick classification of the result shape, e.g. varied, flat, sparse, tiny, or empty.",
    )
    events: list[EventItem] = Field(
        default_factory=list,
        description="Optional offline events aligned to the returned date range.",
    )
    event_comparison: Optional[EventComparison] = Field(
        None,
        description="Optional before/after comparison around the selected event.",
    )
    message: Optional[str] = Field(
        None,
        description="Status message (present only on empty/edge-case results).",
    )
