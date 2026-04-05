"""
Offline event loader for lightweight trend overlays.
"""
from __future__ import annotations

import json
import os

from app.models.events_models import EventItem

EVENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "events.json")


def load_events() -> list[EventItem]:
    path = os.path.abspath(EVENTS_PATH)
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return []

    if not isinstance(payload, list):
        return []

    events: list[EventItem] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            events.append(EventItem(**item))
        except Exception:
            continue
    return events
