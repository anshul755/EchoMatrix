"""
Explainable network analysis for investigative dashboards.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Literal
from urllib.parse import urlparse

import networkx as nx
import pandas as pd

from app.models.network_models import (
    NetworkEdge,
    NetworkMeta,
    NetworkNode,
    NetworkResilience,
    NetworkResponse,
)
from app.services.data_loader import load_data

GraphType = Literal["account", "hashtag", "url", "post", "topic"]
ScoreType = Literal["pagerank", "betweenness"]

GRAPH_METHOD = "NetworkX graph construction + PageRank/betweenness + Louvain communities"
GRAPH_RATIONALE = (
    "PageRank is the default because it is stable, explainable, and highlights influential nodes "
    "without overreacting to noisy local structure. Betweenness is also returned to surface bridge nodes."
)
RELATIONSHIP_STRATEGY = [
    "author-author edges are inferred from shared hashtags, shared URLs, and fallback same-day co-activity when direct interaction data is absent.",
    "author-hashtag and author-URL relationships are used as evidence when building account and URL graphs.",
    "post-post edges are inferred from shared hashtags, shared topic labels, shared authors, and Reddit crosspost links when present.",
    "topic nodes come from Reddit link flair text when available; unlabeled posts fall back to '(unlabeled)'.",
]
MISSING_RELATIONSHIPS = [
    "The dataset contains Reddit submissions only, so there is no native reply graph.",
    "There are no explicit @mentions in structured fields; mention relationships would need NLP extraction.",
    "Repost relationships are only partially available via crosspost_parent and crosspost_parent_list.",
]


def analyze_network(
    query: str = "",
    graph_type: GraphType = "account",
    scoring: ScoreType = "pagerank",
    min_degree: int = 1,
    remove_top_node: bool = False,
) -> NetworkResponse:
    frame = load_data()
    if frame.empty:
        return _empty_response(query, graph_type, scoring, "No posts are available for network analysis.")

    working = frame.copy()
    if query.strip():
        mask = working["text"].fillna("").str.contains(
            query.strip(),
            case=False,
            na=False,
            regex=False,
        )
        working = working[mask]

    if working.empty:
        return _empty_response(query, graph_type, scoring, f'No posts matched query "{query.strip()}".')

    graph = _build_graph(working.reset_index(drop=True), graph_type)
    if graph.number_of_nodes() == 0:
        return _empty_response(query, graph_type, scoring, "The selected graph type did not produce any nodes.")

    if min_degree > 0:
        removable = [node for node, degree in graph.degree() if degree < min_degree]
        graph.remove_nodes_from(removable)

    if graph.number_of_nodes() == 0:
        return _empty_response(query, graph_type, scoring, "All nodes were removed by the minimum degree filter.")

    graph = _cap_graph(graph, max_nodes=300)
    pagerank = _safe_pagerank(graph)
    betweenness = _safe_betweenness(graph)
    communities, node_community = _safe_communities(graph)
    components = list(nx.connected_components(graph)) if graph.number_of_nodes() else []
    component_lookup = _component_lookup(components)

    nodes = _serialize_nodes(graph, pagerank, betweenness, node_community, component_lookup, scoring)
    edges = _serialize_edges(graph)
    resilience = _resilience_report(graph, scoring) if remove_top_node else None

    sparse_graph = graph.number_of_edges() < max(1, graph.number_of_nodes() - 1)
    disconnected_graph = len(components) > 1
    largest_component = max((len(component) for component in components), default=0)

    message = None
    if sparse_graph and disconnected_graph:
        message = "Graph is sparse and disconnected, so centrality scores should be interpreted cautiously."
    elif sparse_graph:
        message = "Graph is sparse; edge evidence is limited."
    elif disconnected_graph:
        message = "Graph has multiple disconnected components."

    return NetworkResponse(
        query=query,
        total_nodes=len(nodes),
        total_edges=len(edges),
        communities=communities,
        nodes=nodes,
        edges=edges,
        meta=NetworkMeta(
            graph_type=graph_type,
            scoring=scoring,
            method=GRAPH_METHOD,
            rationale=GRAPH_RATIONALE,
            relationship_strategy=RELATIONSHIP_STRATEGY,
            missing_relationships=MISSING_RELATIONSHIPS,
            sparse_graph=sparse_graph,
            disconnected_graph=disconnected_graph,
            total_components=len(components),
            largest_component_size=largest_component,
            filtered_posts=len(working),
            message=message,
        ),
        resilience=resilience,
    )


def _build_graph(frame: pd.DataFrame, graph_type: GraphType) -> nx.Graph:
    builders = {
        "account": _build_account_graph,
        "hashtag": _build_hashtag_graph,
        "url": _build_url_graph,
        "post": _build_post_graph,
        "topic": _build_topic_graph,
    }
    return builders[graph_type](frame)


def _build_account_graph(frame: pd.DataFrame) -> nx.Graph:
    graph = nx.Graph()
    hashtag_authors: dict[str, set[str]] = defaultdict(set)
    url_authors: dict[str, set[str]] = defaultdict(set)
    topic_authors: dict[str, set[str]] = defaultdict(set)
    day_authors: dict[str, set[str]] = defaultdict(set)
    author_posts = Counter()

    for _, row in frame.iterrows():
        author = _clean_author(row.get("author"))
        if not author:
            continue
        author_posts[author] += 1
        graph.add_node(author, type="account", label=author, post_count=author_posts[author])

        for tag in _hashtags(row.get("hashtags")):
            hashtag_authors[tag].add(author)

        url = _url_key(row.get("url"))
        if url:
            url_authors[url].add(author)

        topic = _topic_key(row)
        if topic:
            topic_authors[topic].add(author)

        date = row.get("date")
        if not pd.isna(date):
            day_authors[str(pd.Timestamp(date).date())].add(author)

    for tag, authors in hashtag_authors.items():
        _add_clique_edges(graph, authors, evidence=f"shared hashtag:{tag}", weight=1.0)

    for url, authors in url_authors.items():
        _add_clique_edges(graph, authors, evidence=f"shared url:{url}", weight=1.5)

    for topic, authors in topic_authors.items():
        _add_clique_edges(graph, authors, evidence=f"shared topic:{topic}", weight=1.0, limit=20)

    if graph.number_of_edges() < 5:
        for day, authors in day_authors.items():
            _add_clique_edges(graph, authors, evidence=f"same day:{day}", weight=0.5, limit=15)

    _refresh_post_counts(graph, author_posts)
    return graph


def _build_hashtag_graph(frame: pd.DataFrame) -> nx.Graph:
    graph = nx.Graph()
    tag_posts = Counter()

    for _, row in frame.iterrows():
        tags = sorted(set(_hashtags(row.get("hashtags"))))
        for tag in tags:
            tag_posts[tag] += 1
            graph.add_node(tag, type="hashtag", label=f"#{tag}", post_count=tag_posts[tag])
        for left, right in combinations(tags[:12], 2):
            _bump_edge(graph, left, right, evidence="co-occurred in post", weight=1.0)

    _refresh_post_counts(graph, tag_posts)
    return graph


def _build_url_graph(frame: pd.DataFrame) -> nx.Graph:
    graph = nx.Graph()
    url_posts = Counter()
    author_urls: dict[str, set[str]] = defaultdict(set)
    tag_urls: dict[str, set[str]] = defaultdict(set)

    for _, row in frame.iterrows():
        url = _url_key(row.get("url"))
        if not url:
            continue
        url_posts[url] += 1
        graph.add_node(url, type="url", label=url, post_count=url_posts[url])

        author = _clean_author(row.get("author"))
        if author:
            author_urls[author].add(url)

        for tag in _hashtags(row.get("hashtags")):
            tag_urls[tag].add(url)

    for author, urls in author_urls.items():
        _add_clique_edges(graph, urls, evidence=f"shared author:{author}", weight=1.0)

    for tag, urls in tag_urls.items():
        _add_clique_edges(graph, urls, evidence=f"shared hashtag:{tag}", weight=1.0, limit=12)

    _refresh_post_counts(graph, url_posts)
    return graph


def _build_topic_graph(frame: pd.DataFrame) -> nx.Graph:
    graph = nx.Graph()
    topic_posts = Counter()
    author_topics: dict[str, set[str]] = defaultdict(set)
    url_topics: dict[str, set[str]] = defaultdict(set)
    hashtag_topics: dict[str, set[str]] = defaultdict(set)

    for _, row in frame.iterrows():
        topic = _topic_key(row)
        if not topic:
            continue
        topic_posts[topic] += 1
        graph.add_node(topic, type="topic", label=topic, post_count=topic_posts[topic])

        author = _clean_author(row.get("author"))
        if author:
            author_topics[author].add(topic)

        url = _url_key(row.get("url"))
        if url:
            url_topics[url].add(topic)

        for tag in _hashtags(row.get("hashtags")):
            hashtag_topics[tag].add(topic)

    for _, topics in author_topics.items():
        _add_clique_edges(graph, topics, evidence="shared author", weight=1.0, limit=12)
    for _, topics in url_topics.items():
        _add_clique_edges(graph, topics, evidence="shared url", weight=1.2, limit=12)
    for _, topics in hashtag_topics.items():
        _add_clique_edges(graph, topics, evidence="shared hashtag", weight=1.0, limit=12)

    _refresh_post_counts(graph, topic_posts)
    return graph


def _build_post_graph(frame: pd.DataFrame) -> nx.Graph:
    graph = nx.Graph()
    id_to_node: dict[str, str] = {}

    for idx, row in frame.iterrows():
        node_id = f"post:{idx}"
        text = str(row.get("text", "")).strip()
        post_id = _clean_optional(row.get("post_id"))
        if post_id:
            id_to_node[post_id] = node_id
        graph.add_node(
            node_id,
            type="post",
            label=_truncate(text, 60) or node_id,
            post_count=1,
        )

    tag_posts: dict[str, list[str]] = defaultdict(list)
    author_posts: dict[str, list[str]] = defaultdict(list)
    topic_posts: dict[str, list[str]] = defaultdict(list)
    for idx, row in frame.iterrows():
        node_id = f"post:{idx}"
        for tag in _hashtags(row.get("hashtags")):
            tag_posts[tag].append(node_id)
        author = _clean_author(row.get("author"))
        if author:
            author_posts[author].append(node_id)
        topic = _topic_key(row)
        if topic:
            topic_posts[topic].append(node_id)
        parent = _crosspost_parent_id(row)
        if parent and parent in id_to_node:
            _bump_edge(graph, node_id, id_to_node[parent], evidence="crosspost relationship", weight=2.0)

    for tag, posts in tag_posts.items():
        _add_clique_edges(graph, posts, evidence=f"shared hashtag:{tag}", weight=1.0, limit=10)

    for topic, posts in topic_posts.items():
        _add_clique_edges(graph, posts, evidence=f"shared topic:{topic}", weight=1.2, limit=12)

    if graph.number_of_edges() < 5:
        for author, posts in author_posts.items():
            _add_clique_edges(graph, posts, evidence=f"shared author:{author}", weight=0.8, limit=8)

    return graph


def _serialize_nodes(
    graph: nx.Graph,
    pagerank: dict[str, float],
    betweenness: dict[str, float],
    node_community: dict[str, int],
    component_lookup: dict[str, int],
    scoring: ScoreType,
) -> list[NetworkNode]:
    nodes: list[NetworkNode] = []
    ranked = sorted(
        graph.nodes(),
        key=lambda node: (pagerank.get(node, 0.0), graph.degree(node)),
        reverse=True,
    )
    for node in ranked:
        nodes.append(
            NetworkNode(
                id=str(node),
                label=str(graph.nodes[node].get("label", node)),
                type=str(graph.nodes[node].get("type", "entity")),
                pagerank=round(float(pagerank.get(node, 0.0)), 6),
                betweenness=round(float(betweenness.get(node, 0.0)), 6),
                centrality=round(float((pagerank if scoring == "pagerank" else betweenness).get(node, 0.0)), 6),
                community=int(node_community.get(node, 0)),
                degree=int(graph.degree(node)),
                component=int(component_lookup.get(node, 0)),
                post_count=int(graph.nodes[node].get("post_count", 0)),
            )
        )
    return nodes


def _serialize_edges(graph: nx.Graph) -> list[NetworkEdge]:
    edges: list[NetworkEdge] = []
    for source, target, data in graph.edges(data=True):
        edges.append(
            NetworkEdge(
                source=str(source),
                target=str(target),
                weight=round(float(data.get("weight", 1.0)), 4),
                evidence=str(data.get("evidence", "co-occurrence")),
            )
        )
    return sorted(edges, key=lambda edge: edge.weight, reverse=True)


def _resilience_report(graph: nx.Graph, scoring: ScoreType) -> NetworkResilience | None:
    if graph.number_of_nodes() == 0:
        return None

    pagerank = _safe_pagerank(graph)
    betweenness = _safe_betweenness(graph)
    score_map = pagerank if scoring == "pagerank" else betweenness
    top_node = max(score_map, key=score_map.get, default=None)
    if top_node is None:
        return None

    original_components = list(nx.connected_components(graph))
    original_largest = max((len(component) for component in original_components), default=0)

    updated = graph.copy()
    updated.remove_node(top_node)
    updated_components = list(nx.connected_components(updated)) if updated.number_of_nodes() else []
    updated_largest = max((len(component) for component in updated_components), default=0)

    return NetworkResilience(
        removed_node=str(top_node),
        original_largest_component=original_largest,
        updated_largest_component=updated_largest,
        original_components=len(original_components),
        updated_components=len(updated_components),
        changed=(original_largest != updated_largest or len(original_components) != len(updated_components)),
    )


def _safe_pagerank(graph: nx.Graph) -> dict[str, float]:
    try:
        return nx.pagerank(graph, weight="weight")
    except Exception:
        node_count = max(graph.number_of_nodes(), 1)
        return {str(node): 1.0 / node_count for node in graph.nodes()}


def _safe_betweenness(graph: nx.Graph) -> dict[str, float]:
    try:
        return nx.betweenness_centrality(graph, weight="weight")
    except Exception:
        return {str(node): 0.0 for node in graph.nodes()}


def _safe_communities(graph: nx.Graph) -> tuple[int, dict[str, int]]:
    try:
        from networkx.algorithms.community import louvain_communities

        communities = louvain_communities(graph, weight="weight", seed=42)
        lookup: dict[str, int] = {}
        for community_id, members in enumerate(communities):
            for member in members:
                lookup[str(member)] = community_id
        return len(communities), lookup
    except Exception:
        lookup = {str(node): 0 for node in graph.nodes()}
        return 1 if graph.number_of_nodes() else 0, lookup


def _cap_graph(graph: nx.Graph, max_nodes: int) -> nx.Graph:
    if graph.number_of_nodes() <= max_nodes:
        return graph
    ranked = sorted(graph.degree(), key=lambda item: item[1], reverse=True)
    keep = {node for node, _ in ranked[:max_nodes]}
    return graph.subgraph(keep).copy()


def _component_lookup(components: list[set[str]]) -> dict[str, int]:
    lookup: dict[str, int] = {}
    for component_id, component in enumerate(sorted(components, key=len, reverse=True)):
        for node in component:
            lookup[str(node)] = component_id
    return lookup


def _empty_response(query: str, graph_type: GraphType, scoring: ScoreType, message: str) -> NetworkResponse:
    return NetworkResponse(
        query=query,
        nodes=[],
        edges=[],
        total_nodes=0,
        total_edges=0,
        communities=0,
        meta=NetworkMeta(
            graph_type=graph_type,
            scoring=scoring,
            method=GRAPH_METHOD,
            rationale=GRAPH_RATIONALE,
            relationship_strategy=RELATIONSHIP_STRATEGY,
            missing_relationships=MISSING_RELATIONSHIPS,
            filtered_posts=0,
            message=message,
        ),
    )


def _add_clique_edges(
    graph: nx.Graph,
    nodes,
    evidence: str,
    weight: float,
    limit: int | None = None,
) -> None:
    unique_nodes = list(dict.fromkeys(node for node in nodes if node))
    if limit is not None:
        unique_nodes = unique_nodes[:limit]
    for left, right in combinations(unique_nodes, 2):
        _bump_edge(graph, left, right, evidence=evidence, weight=weight)


def _bump_edge(graph: nx.Graph, left: str, right: str, evidence: str, weight: float) -> None:
    if left == right:
        return
    if graph.has_edge(left, right):
        graph[left][right]["weight"] += weight
    else:
        graph.add_edge(left, right, weight=weight, evidence=evidence)


def _hashtags(value) -> list[str]:
    if not isinstance(value, list):
        return []
    tags = []
    for item in value:
        clean = str(item).strip().lower().lstrip("#")
        if clean:
            tags.append(clean)
    return tags


def _clean_author(value) -> str | None:
    if value is None:
        return None
    author = str(value).strip()
    return author or None


def _clean_optional(value) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    cleaned = str(value).strip()
    return cleaned or None


def _topic_key(row) -> str | None:
    topic = _clean_optional(row.get("link_flair_text")) or _clean_optional(row.get("subreddit_name"))
    return topic or "(unlabeled)"


def _crosspost_parent_id(row) -> str | None:
    raw_post = row.get("raw_post")
    if not isinstance(raw_post, dict):
        return None
    parent = _clean_optional(raw_post.get("crosspost_parent"))
    if parent and parent.startswith("t3_"):
        return parent[3:]
    return parent


def _url_key(value) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw)
    except ValueError:
        return raw[:120]
    host = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.rstrip("/")
    if host:
        return f"{host}{path}" if path else host
    return raw[:120]


def _truncate(text: str, length: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= length:
        return compact
    return compact[: length - 3].rstrip() + "..."


def _refresh_post_counts(graph: nx.Graph, counts: Counter) -> None:
    for node in graph.nodes():
        graph.nodes[node]["post_count"] = int(counts.get(node, 0))
