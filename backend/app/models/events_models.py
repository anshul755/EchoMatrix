"""
Pydantic models for offline event overlays.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EventItem(BaseModel):
    id: str
    date: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None


class EventComparison(BaseModel):
    event_id: str
    event_title: str
    before_total: int = 0
    after_total: int = 0
    delta: int = 0
    change_ratio: Optional[float] = None
    window_buckets: int = Field(3, description="Buckets compared before and after the event.")


class EventsResponse(BaseModel):
    events: list[EventItem] = Field(default_factory=list)
    message: Optional[str] = None
