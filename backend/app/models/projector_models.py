"""
Pydantic models for TensorFlow Projector export metadata.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ProjectorRecommendation(BaseModel):
    option: str = Field(..., description="Recommended visualization tool.")
    reason: str = Field(..., description="Why this option is the best fit for the stack.")


class ProjectorFiles(BaseModel):
    vectors_tsv_url: str
    metadata_tsv_url: str
    projector_url: str


class ProjectorExportResponse(BaseModel):
    recommendation: ProjectorRecommendation
    files: ProjectorFiles
    total_posts: int
    exported_points: int
    requested_clusters: int
    actual_clusters: int
    metadata_format: str
    integration_strategy: str
    large_dataset_strategy: str
    cluster_interpretation_note: str
    message: Optional[str] = None
