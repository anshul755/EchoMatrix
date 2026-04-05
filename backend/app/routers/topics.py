"""Topic clustering endpoint."""
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.routers._cache_utils import ResponseCache
from app.models.projector_models import ProjectorExportResponse
from app.models.topics_models import TopicClusteringResponse
from app.services.projector_export import build_projector_export, get_projector_export_manifest
from app.services.topic_clustering import cluster_posts

router = APIRouter()
_TOPICS_CACHE = ResponseCache(ttl_seconds=180.0)
_PROJECTOR_CACHE = ResponseCache(ttl_seconds=180.0)


@router.get("/topics", response_model=TopicClusteringResponse)
async def get_topics(
    n_clusters: int = Query(
        8,
        ge=1,
        description="Requested number of clusters. Oversized requests are clipped safely in the clustering service.",
    ),
) -> TopicClusteringResponse:
    cache_key = f"topics:{n_clusters}"
    cached = _TOPICS_CACHE.get(cache_key)
    if cached is not None:
        return cached
    response = cluster_posts(requested_clusters=n_clusters)
    _TOPICS_CACHE.set(cache_key, response)
    return response


@router.get("/topics/projector", response_model=ProjectorExportResponse)
async def get_projector_manifest(
    n_clusters: int = Query(
        8,
        ge=1,
        description="Requested number of clusters. Oversized requests are clipped safely in the clustering service.",
    ),
    max_points: int = Query(2000, ge=100, le=5000, description="Maximum points to export."),
) -> ProjectorExportResponse:
    cache_key = f"projector-manifest:{n_clusters}:{max_points}"
    cached = _PROJECTOR_CACHE.get(cache_key)
    if cached is not None:
        return cached
    response = get_projector_export_manifest(
        base_path="/api/topics/projector",
        requested_clusters=n_clusters,
        max_points=max_points,
    )
    _PROJECTOR_CACHE.set(cache_key, response)
    return response


@router.get("/topics/projector/vectors.tsv", response_class=PlainTextResponse)
async def get_projector_vectors(
    n_clusters: int = Query(8, ge=1),
    max_points: int = Query(2000, ge=100, le=5000),
) -> PlainTextResponse:
    cache_key = f"projector-vectors:{n_clusters}:{max_points}"
    export = _PROJECTOR_CACHE.get(cache_key)
    if export is None:
        export = build_projector_export(requested_clusters=n_clusters, max_points=max_points)
        _PROJECTOR_CACHE.set(cache_key, export)
    return PlainTextResponse(export["vectors_tsv"], media_type="text/tab-separated-values")


@router.get("/topics/projector/metadata.tsv", response_class=PlainTextResponse)
async def get_projector_metadata(
    n_clusters: int = Query(8, ge=1),
    max_points: int = Query(2000, ge=100, le=5000),
) -> PlainTextResponse:
    cache_key = f"projector-metadata:{n_clusters}:{max_points}"
    export = _PROJECTOR_CACHE.get(cache_key)
    if export is None:
        export = build_projector_export(requested_clusters=n_clusters, max_points=max_points)
        _PROJECTOR_CACHE.set(cache_key, export)
    return PlainTextResponse(export["metadata_tsv"], media_type="text/tab-separated-values")
