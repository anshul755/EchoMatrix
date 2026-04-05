"""
Pydantic models for topic clustering responses.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TopicRepresentativePost(BaseModel):
    """A representative post selected from within a cluster."""

    text: str = Field(..., description="Representative post text, truncated for display.")
    author: Optional[str] = Field(None, description="Author username when available.")
    date: Optional[str] = Field(None, description="Post date as an ISO string.")
    url: Optional[str] = Field(None, description="Link to the original post.")
    platform: Optional[str] = Field(None, description="Source platform or subreddit.")
    score: float = Field(
        ..., description="Similarity to the cluster centroid, where higher means more central."
    )


class TopicClusterMetadata(BaseModel):
    """Useful, lightweight metadata about a cluster."""

    share_of_posts: float = Field(..., description="Fraction of all clustered posts in this cluster.")
    cohesion_score: float = Field(
        ..., description="Average cosine similarity between cluster posts and the centroid."
    )
    average_post_length: int = Field(..., description="Average post length in characters.")
    top_platforms: list[str] = Field(
        default_factory=list,
        description="Most common platforms or subreddits represented in the cluster.",
    )


class TopicCluster(BaseModel):
    """One topic cluster."""

    id: int = Field(..., description="Stable cluster id within the response.")
    label: str = Field(..., description="Human-friendly summary label for the cluster.")
    keywords: list[str] = Field(
        default_factory=list, description="Top keywords extracted from cluster text."
    )
    summary: str = Field(..., description="Short explanation of what the cluster is about.")
    count: int = Field(..., description="Number of posts assigned to the cluster.")
    representative_posts: list[TopicRepresentativePost] = Field(
        default_factory=list,
        description="A few central posts that represent the cluster well.",
    )
    metadata: TopicClusterMetadata = Field(..., description="Useful cluster metadata.")


class TopicEmbeddingPoint(BaseModel):
    """2D projected point for dashboard visualization."""

    x: float
    y: float
    cluster: int


class TopicClusteringResponse(BaseModel):
    """Top-level response for topic clustering."""

    requested_clusters: int = Field(..., description="Cluster count requested by the client.")
    actual_clusters: int = Field(..., description="Cluster count used after safe adjustment.")
    total_posts: int = Field(..., description="Total number of posts available for clustering.")
    clustered_posts: int = Field(..., description="Number of non-empty posts clustered.")
    clustering_method: str = Field(
        ..., description="Short description of the clustering approach used."
    )
    parameter_notes: list[str] = Field(
        default_factory=list,
        description="Short explanation of the key clustering parameters and safety guards used.",
    )
    message: Optional[str] = Field(
        None,
        description="Optional human-readable note about empty data or cluster-count adjustment.",
    )
    clusters: list[TopicCluster] = Field(default_factory=list, description="Cluster results.")
    embeddings_2d: list[TopicEmbeddingPoint] = Field(
        default_factory=list,
        description="Optional 2D embedding projection for visualization.",
    )
