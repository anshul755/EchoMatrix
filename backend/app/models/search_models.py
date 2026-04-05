"""
Pydantic models for the semantic search endpoint.

Provides a clean, typed contract that:
  - Validates incoming query parameters
  - Structures the JSON response for clients / chatbot UIs
  - Documents every field with descriptions for OpenAPI auto-docs
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ── Request ─────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    """Query parameters accepted by GET /api/search."""

    query: str = Field("", description="Free-text search query.")
    limit: int = Field(20, ge=1, le=100, description="Max results to return.")
    author: Optional[str] = Field(None, description="Filter by author username.")
    platform: Optional[str] = Field(None, description="Filter by platform (e.g. r/politics).")
    date_from: Optional[date] = Field(None, description="Earliest date (YYYY-MM-DD).")
    date_to: Optional[date] = Field(None, description="Latest date (YYYY-MM-DD).")


# ── Response items ──────────────────────────────────────────────
class SearchResultMetadata(BaseModel):
    """Structured metadata attached to each result."""

    post_id: Optional[str] = Field(None, description="Canonical post id.")
    subreddit: Optional[str] = Field(None, description="Subreddit/community name.")
    domain: Optional[str] = Field(None, description="Link domain when available.")
    is_self_post: Optional[bool] = Field(None, description="Whether the result is a Reddit self-post.")
    comment_count: Optional[int] = Field(None, description="Snapshot comment count.")
    score_value: Optional[int] = Field(None, description="Snapshot Reddit score.")
    media_type: Optional[str] = Field(None, description="Derived media classification.")


class SearchResultItem(BaseModel):
    """A single search result with snippet and metadata."""

    text: str = Field(..., description="Full text of the post (truncated to 500 chars).")
    snippet: str = Field(
        ..., description="Short excerpt (~200 chars) centred on the matching region."
    )
    author: Optional[str] = Field(None, description="Post author username.")
    date: Optional[str] = Field(None, description="Post date as ISO string (YYYY-MM-DD).")
    url: Optional[str] = Field(None, description="Link to the original post.")
    score: float = Field(..., description="Semantic similarity score (0-1, higher = more relevant).")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags extracted from the post.")
    platform: Optional[str] = Field(None, description="Source platform (e.g. r/news).")
    metadata: SearchResultMetadata = Field(
        default_factory=SearchResultMetadata,
        description="Additional canonical metadata for the matched post.",
    )


class SearchResponse(BaseModel):
    """Top-level response envelope for search results.

    This contract is stable enough for a chatbot or frontend to rely on.
    """

    query: str = Field(..., description="Echo of the original query.")
    results: list[SearchResultItem] = Field(
        default_factory=list, description="Ranked search results."
    )
    total: int = Field(0, description="Number of results returned.")
    message: Optional[str] = Field(
        None,
        description="Human-readable status message (present when results are empty or query is invalid).",
    )
    related_queries: list[str] = Field(
        default_factory=list,
        description="2-3 suggested follow-up queries (powered by LLM when available).",
    )
    retrieval_method: Optional[str] = Field(
        None,
        description="Retrieval strategy used for this response, including fallback mode when applicable.",
    )
