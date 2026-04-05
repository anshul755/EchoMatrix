"""Network analysis endpoint."""
from fastapi import APIRouter, Query

from app.routers._cache_utils import ResponseCache
from app.models.network_models import NetworkResponse
from app.services.network_analysis import analyze_network

router = APIRouter()
_NETWORK_CACHE = ResponseCache(ttl_seconds=120.0)


@router.get("/network", response_model=NetworkResponse)
async def get_network(
    q: str = Query("", description="Optional topic filter"),
    min_degree: int = Query(1, ge=0, description="Minimum node degree"),
    graph_type: str = Query("account", pattern="^(account|hashtag|url|post|topic)$"),
    scoring: str = Query("pagerank", pattern="^(pagerank|betweenness)$"),
    remove_top_node: bool = Query(False, description="Remove top-scoring node and re-evaluate graph."),
) -> NetworkResponse:
    cache_key = "|".join(
        [
            f"q={q.strip()}",
            f"min_degree={min_degree}",
            f"graph_type={graph_type}",
            f"scoring={scoring}",
            f"remove_top_node={remove_top_node}",
        ]
    )
    cached = _NETWORK_CACHE.get(cache_key)
    if cached is not None:
        return cached
    response = analyze_network(
        query=q,
        graph_type=graph_type,
        scoring=scoring,
        min_degree=min_degree,
        remove_top_node=remove_top_node,
    )
    _NETWORK_CACHE.set(cache_key, response)
    return response
