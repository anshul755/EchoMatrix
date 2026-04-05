"""
Pydantic models for network analysis responses.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class NetworkNode(BaseModel):
    id: str
    label: str
    type: str = Field(..., description="Node type such as account, hashtag, url, or post.")
    pagerank: float = 0.0
    betweenness: float = 0.0
    centrality: float = Field(..., description="Primary score selected for the response.")
    community: int = 0
    degree: int = 0
    component: int = 0
    post_count: int = 0


class NetworkEdge(BaseModel):
    source: str
    target: str
    weight: float = 1.0
    evidence: str = Field(..., description="Short explanation of why the edge exists.")


class NetworkResilience(BaseModel):
    removed_node: Optional[str] = None
    original_largest_component: int = 0
    updated_largest_component: int = 0
    original_components: int = 0
    updated_components: int = 0
    changed: bool = False


class NetworkMeta(BaseModel):
    graph_type: Literal["account", "hashtag", "url", "post", "topic"]
    scoring: Literal["pagerank", "betweenness"]
    method: str
    rationale: str
    relationship_strategy: list[str] = Field(
        default_factory=list,
        description="Which raw dataset relationships were turned into graph edges.",
    )
    missing_relationships: list[str] = Field(
        default_factory=list,
        description="Relationships requested conceptually but not actually present in the Reddit submission dataset.",
    )
    sparse_graph: bool = False
    disconnected_graph: bool = False
    total_components: int = 0
    largest_component_size: int = 0
    filtered_posts: int = 0
    message: Optional[str] = None


class NetworkResponse(BaseModel):
    query: str = ""
    total_nodes: int = 0
    total_edges: int = 0
    communities: int = 0
    nodes: list[NetworkNode] = Field(default_factory=list)
    edges: list[NetworkEdge] = Field(default_factory=list)
    meta: NetworkMeta
    resilience: Optional[NetworkResilience] = None
