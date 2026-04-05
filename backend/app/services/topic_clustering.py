"""
Simple, explainable topic clustering built on embeddings + KMeans.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer

from app.models.topics_models import (
    TopicCluster,
    TopicClusterMetadata,
    TopicClusteringResponse,
    TopicEmbeddingPoint,
    TopicRepresentativePost,
)
from app.services.data_loader import load_data
from app.services.embeddings import get_provider

DEFAULT_CLUSTERS = 8
MAX_CLUSTERS = 50
MAX_REPRESENTATIVES = 3
MIN_CLUSTERABLE_POSTS = 2

STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "must", "need", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "about", "above", "below", "between",
    "out", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "it",
    "its", "this", "that", "these", "those", "i", "me", "my", "we", "our",
    "you", "your", "he", "him", "his", "she", "her", "they", "them",
    "their", "what", "which", "who", "whom", "and", "but", "or", "if",
    "because", "while", "although", "http", "https", "www", "com", "amp",
    "reddit", "post", "posts", "wouldn", "couldn", "shouldn",
}


def cluster_posts(
    requested_clusters: int = DEFAULT_CLUSTERS,
    representative_posts_limit: int = MAX_REPRESENTATIVES,
) -> TopicClusteringResponse:
    """Cluster posts into topics with safe behavior for small datasets."""
    safe_requested = int(np.clip(requested_clusters, 1, MAX_CLUSTERS))
    representative_posts_limit = int(np.clip(representative_posts_limit, 1, MAX_REPRESENTATIVES))
    parameter_notes = [
        "Embeddings come from each post's normalized text field, which is built from title plus selftext in backend/data/data.jsonl.",
        f"KMeans uses a fixed random_state=42 and n_init=10 for stable, interview-friendly clustering.",
        f"Requested clusters are clipped to 1-{MAX_CLUSTERS} and further reduced when the corpus is too small or too repetitive.",
        f"Representative posts are the centroid-nearest posts, capped at {representative_posts_limit} per cluster.",
    ]

    df = load_data()
    if df.empty:
        return TopicClusteringResponse(
            requested_clusters=safe_requested,
            actual_clusters=0,
            total_posts=0,
            clustered_posts=0,
            clustering_method="Embedding + KMeans",
            parameter_notes=parameter_notes,
            message="No posts are available for clustering.",
            clusters=[],
            embeddings_2d=[],
        )

    working = df.copy()
    working["text"] = working["text"].fillna("").astype(str).map(_clean_text)
    working = working[working["text"].str.len() > 0].reset_index(drop=True)
    total_posts = len(df)

    if working.empty:
        return TopicClusteringResponse(
            requested_clusters=safe_requested,
            actual_clusters=0,
            total_posts=total_posts,
            clustered_posts=0,
            clustering_method="Embedding + KMeans",
            parameter_notes=parameter_notes,
            message="All available posts were empty after cleaning.",
            clusters=[],
            embeddings_2d=[],
        )

    if len(working) < MIN_CLUSTERABLE_POSTS:
        single_clusters = _build_singleton_clusters(working)
        return TopicClusteringResponse(
            requested_clusters=safe_requested,
            actual_clusters=len(single_clusters),
            total_posts=total_posts,
            clustered_posts=len(working),
            clustering_method="Embedding + KMeans with singleton fallback",
            parameter_notes=parameter_notes,
            message="Too few records for multi-cluster modeling, so each available post was treated as its own topic.",
            clusters=single_clusters,
            embeddings_2d=_singleton_points(len(single_clusters)),
        )

    texts = working["text"].tolist()
    embeddings = get_provider().embed_corpus(texts)
    unique_text_count = len({text.lower() for text in texts})
    actual_clusters = min(safe_requested, len(texts), max(unique_text_count, 1))

    if len(texts) == 1 or actual_clusters == 1:
        labels = np.array([0], dtype=int)
        if len(texts) > 1:
            labels = np.zeros(len(texts), dtype=int)
        centroids = np.mean(embeddings, axis=0, keepdims=True) if embeddings.size else np.ones((1, 1), dtype=np.float32)
    else:
        model = KMeans(n_clusters=actual_clusters, random_state=42, n_init=10)
        labels = model.fit_predict(embeddings)
        centroids = np.asarray(model.cluster_centers_, dtype=np.float32)

    order = _cluster_order(labels)
    label_map = {original: new for new, original in enumerate(order)}
    remapped_labels = np.array([label_map[int(label)] for label in labels], dtype=int)
    ordered_centroids = np.asarray([centroids[cluster_id] for cluster_id in order], dtype=np.float32)

    message = None
    if actual_clusters != safe_requested:
        message = (
            f"Requested {safe_requested} clusters, but used {actual_clusters} "
            f"for {len(texts)} non-empty posts ({unique_text_count} distinct normalized texts)."
        )

    clusters = _build_clusters(
        frame=working,
        texts=texts,
        embeddings=embeddings,
        labels=remapped_labels,
        centroids=ordered_centroids,
        representative_posts_limit=representative_posts_limit,
    )

    return TopicClusteringResponse(
        requested_clusters=safe_requested,
        actual_clusters=actual_clusters,
        total_posts=total_posts,
        clustered_posts=len(texts),
        clustering_method="Sentence embeddings + KMeans with centroid-based representatives",
        parameter_notes=parameter_notes,
        message=message,
        clusters=clusters,
        embeddings_2d=_project_points(embeddings, remapped_labels),
    )


def _build_clusters(
    frame,
    texts: list[str],
    embeddings: np.ndarray,
    labels: np.ndarray,
    centroids: np.ndarray,
    representative_posts_limit: int,
) -> list[TopicCluster]:
    clusters: list[TopicCluster] = []
    total_posts = len(texts)
    cluster_count = int(labels.max()) + 1 if len(labels) else 0

    for cluster_id in range(cluster_count):
        indices = np.flatnonzero(labels == cluster_id)
        cluster_texts = [texts[i] for i in indices]
        keywords = _extract_keywords(cluster_texts)
        centroid = centroids[cluster_id]
        representative_posts, cohesion_score = _representative_posts(
            frame=frame,
            embeddings=embeddings,
            centroid=centroid,
            indices=indices,
            limit=representative_posts_limit,
        )
        summary = _build_summary(keywords, representative_posts)
        platforms = _top_values(frame.iloc[indices]["platform"].tolist(), limit=3)
        average_post_length = int(round(np.mean([len(texts[i]) for i in indices]))) if len(indices) else 0

        clusters.append(
            TopicCluster(
                id=cluster_id,
                label=_build_label(cluster_id, keywords, representative_posts),
                keywords=keywords,
                summary=summary,
                count=len(indices),
                representative_posts=representative_posts,
                metadata=TopicClusterMetadata(
                    share_of_posts=round(len(indices) / total_posts, 4),
                    cohesion_score=round(cohesion_score, 4),
                    average_post_length=average_post_length,
                    top_platforms=platforms,
                ),
            )
        )

    return clusters


def _representative_posts(frame, embeddings, centroid, indices, limit: int):
    centroid = np.asarray(centroid, dtype=np.float32)
    norm = np.linalg.norm(centroid)
    if norm > 0:
        centroid = centroid / norm

    cluster_embeddings = embeddings[indices]
    scores = cluster_embeddings @ centroid if cluster_embeddings.size else np.zeros(len(indices))
    order = np.argsort(scores)[::-1]

    reps: list[TopicRepresentativePost] = []
    seen_post_ids: set[str] = set()
    for rank in order[:limit]:
        idx = int(indices[rank])
        row = frame.iloc[idx]
        post_id = _clean_optional(row.get("post_id"))
        if post_id and post_id in seen_post_ids:
            continue
        if post_id:
            seen_post_ids.add(post_id)
        reps.append(
            TopicRepresentativePost(
                text=_truncate_text(str(row["text"]), 240),
                author=_clean_optional(row.get("author")),
                date=_format_date(row.get("date")),
                url=_clean_optional(row.get("url")),
                platform=_clean_optional(row.get("platform")),
                score=round(float(scores[rank]), 4),
            )
        )

    cohesion = float(scores.mean()) if len(scores) else 0.0
    return reps, max(0.0, min(1.0, cohesion))


def _build_singleton_clusters(frame) -> list[TopicCluster]:
    clusters: list[TopicCluster] = []
    total_posts = len(frame)
    for idx, (_, row) in enumerate(frame.iterrows()):
        text = _clean_text(str(row.get("text", "")))
        representative = TopicRepresentativePost(
            text=_truncate_text(text, 240),
            author=_clean_optional(row.get("author")),
            date=_format_date(row.get("date")),
            url=_clean_optional(row.get("url")),
            platform=_clean_optional(row.get("platform")),
            score=1.0,
        )
        keywords = _extract_keywords([text])
        clusters.append(
            TopicCluster(
                id=idx,
                label=_build_label(idx, keywords, [representative]),
                keywords=keywords,
                summary=_build_summary(keywords, [representative]),
                count=1,
                representative_posts=[representative],
                metadata=TopicClusterMetadata(
                    share_of_posts=round(1 / total_posts, 4),
                    cohesion_score=1.0,
                    average_post_length=len(text),
                    top_platforms=[_clean_optional(row.get("platform"))] if _clean_optional(row.get("platform")) else [],
                ),
            )
        )
    return clusters


def _singleton_points(count: int) -> list[TopicEmbeddingPoint]:
    if count <= 0:
        return []
    if count == 1:
        return [TopicEmbeddingPoint(x=0.0, y=0.0, cluster=0)]
    return [
        TopicEmbeddingPoint(x=float(idx), y=0.0, cluster=idx)
        for idx in range(count)
    ]


def _project_points(embeddings: np.ndarray, labels: np.ndarray) -> list[TopicEmbeddingPoint]:
    if len(embeddings) == 0:
        return []
    if len(embeddings) == 1:
        return [TopicEmbeddingPoint(x=0.0, y=0.0, cluster=int(labels[0]))]

    coords = PCA(n_components=2, random_state=42).fit_transform(embeddings)
    return [
        TopicEmbeddingPoint(
            x=float(coords[i, 0]),
            y=float(coords[i, 1]),
            cluster=int(labels[i]),
        )
        for i in range(len(coords))
    ]


def _extract_keywords(texts: list[str], top_n: int = 5) -> list[str]:
    if not texts:
        return []

    try:
        vectorizer = TfidfVectorizer(
            stop_words=list(STOP_WORDS),
            ngram_range=(1, 2),
            max_features=250,
        )
        matrix = vectorizer.fit_transform(texts)
        scores = np.asarray(matrix.sum(axis=0)).ravel()
        features = np.asarray(vectorizer.get_feature_names_out())
        order = np.argsort(scores)[::-1]
        keywords = [features[i] for i in order if scores[i] > 0]
        return keywords[:top_n]
    except ValueError:
        return []


def _build_label(
    cluster_id: int,
    keywords: list[str],
    representative_posts: list[TopicRepresentativePost],
) -> str:
    if keywords:
        return " / ".join(word.title() for word in keywords[:2])
    if representative_posts:
        seed = representative_posts[0].text.split(".")[0].strip()
        if seed:
            return _truncate_text(seed, 48)
    return f"Topic {cluster_id + 1}"


def _build_summary(
    keywords: list[str],
    representative_posts: list[TopicRepresentativePost],
) -> str:
    if keywords:
        return f"Posts centered on {', '.join(keywords[:3])}."
    if representative_posts:
        return f"Posts similar to: {representative_posts[0].text}"
    return "A small group of semantically similar posts."


def _cluster_order(labels: np.ndarray) -> list[int]:
    counts = Counter(int(label) for label in labels)
    first_seen: dict[int, int] = {}
    for idx, label in enumerate(labels):
        first_seen.setdefault(int(label), idx)
    return sorted(counts, key=lambda cluster_id: (-counts[cluster_id], first_seen[cluster_id]))


def _top_values(values: Iterable[object], limit: int = 3) -> list[str]:
    cleaned = [str(value).strip() for value in values if value is not None and str(value).strip()]
    return [item for item, _ in Counter(cleaned).most_common(limit)]


def _truncate_text(text: str, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _clean_text(text: str) -> str:
    return " ".join(text.split())


def _clean_optional(value) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _format_date(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    cleaned = str(value).strip()
    return cleaned or None
