"""
Offline events endpoint.
"""
from fastapi import APIRouter

from app.models.events_models import EventsResponse
from app.services.events_loader import load_events

router = APIRouter()


@router.get("/events", response_model=EventsResponse)
async def get_events() -> EventsResponse:
    events = load_events()
    if not events:
        return EventsResponse(events=[], message="No offline event data available.")
    return EventsResponse(events=events)
