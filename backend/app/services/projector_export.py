"""
TensorFlow Projector export helpers.
"""
from __future__ import annotations

from collections import defaultdict
from io import StringIO

import numpy as np
from sklearn.cluster import KMeans

from app.models.projector_models import (
    ProjectorExportResponse,
    ProjectorFiles,
    ProjectorRecommendation,
)
from app.services.data_loader import load_data
from app.services.embeddings import get_provider
from app.services.topic_clustering import _build_label, _cluster_order, _extract_keywords

PROJECTOR_URL = "https://projector.tensorflow.org/"
DEFAULT_MAX_POINTS = 2000
MAX_POINTS_LIMIT = 5000


def get_projector_export_manifest(
    base_path: str,
    requested_clusters: int,
    max_points: int,
) -> ProjectorExportResponse:
    export = build_projector_export(requested_clusters=requested_clusters, max_points=max_points)
    files = ProjectorFiles(
        vectors_tsv_url=f"{base_path}/vectors.tsv?n_clusters={export['requested_clusters']}&max_points={export['exported_points']}",
        metadata_tsv_url=f"{base_path}/metadata.tsv?n_clusters={export['requested_clusters']}&max_points={export['exported_points']}",
        projector_url=PROJECTOR_URL,
    )
    return ProjectorExportResponse(
        recommendation=ProjectorRecommendation(
            option="TensorFlow Projector",
            reason=(
                "It is the easiest robust option for a React + FastAPI demo because it only needs TSV exports, "
                "no extra frontend visualization library, and it already looks polished in public demos."
            ),
        ),
        files=files,
        total_posts=export["total_posts"],
        exported_points=export["exported_points"],
        requested_clusters=export["requested_clusters"],
        actual_clusters=export["actual_clusters"],
        metadata_format=(
            "Two TSV files: vectors.tsv with one embedding vector per line and metadata.tsv with tab-separated "
            "columns for cluster, label, author, platform, date, url, and preview text."
        ),
        integration_strategy=(
            "Link to TensorFlow Projector from the Topics dashboard and expose direct download URLs for the TSV files."
        ),
        large_dataset_strategy=(
            "Cap exports to a stratified sample so large datasets stay responsive while still preserving cluster coverage."
        ),
        cluster_interpretation_note=(
            "Viewing the exported points with cluster labels and preview metadata helps analysts see which posts sit near "
            "cluster centers, which clusters overlap, and where outliers live."
        ),
        message=export["message"],
    )


def build_projector_export(requested_clusters: int, max_points: int = DEFAULT_MAX_POINTS) -> dict:
    safe_clusters = max(1, min(int(requested_clusters), 50))
    safe_max_points = max(100, min(int(max_points), MAX_POINTS_LIMIT))

    frame = load_data().copy()
    if frame.empty:
        return {
            "vectors_tsv": "",
            "metadata_tsv": "cluster_id\tcluster_label\tauthor\tplatform\tdate\turl\tpreview\n",
            "requested_clusters": safe_clusters,
            "actual_clusters": 0,
            "total_posts": 0,
            "exported_points": 0,
            "message": "No posts are available for projector export.",
        }

    frame["text"] = frame["text"].fillna("").astype(str).str.strip()
    frame = frame[frame["text"].str.len() > 0].reset_index(drop=True)
    if frame.empty:
        return {
            "vectors_tsv": "",
            "metadata_tsv": "cluster_id\tcluster_label\tauthor\tplatform\tdate\turl\tpreview\n",
            "requested_clusters": safe_clusters,
            "actual_clusters": 0,
            "total_posts": 0,
            "exported_points": 0,
            "message": "All posts were empty after cleaning.",
        }

    texts = frame["text"].tolist()
    embeddings = get_provider().embed_corpus(texts)
    actual_clusters = min(safe_clusters, len(texts))

    if len(texts) == 1:
        labels = np.array([0], dtype=int)
    else:
        model = KMeans(n_clusters=actual_clusters, random_state=42, n_init=10)
        labels = model.fit_predict(embeddings)

    order = _cluster_order(labels)
    label_map = {original: new for new, original in enumerate(order)}
    remapped_labels = np.array([label_map[int(label)] for label in labels], dtype=int)
    cluster_labels = _cluster_label_lookup(texts, remapped_labels)

    indices = _sample_indices(remapped_labels, safe_max_points)
    sampled_embeddings = embeddings[indices]

    vectors_buffer = StringIO()
    for vector in sampled_embeddings:
      vectors_buffer.write("\t".join(f"{float(value):.8f}" for value in vector))
      vectors_buffer.write("\n")

    metadata_buffer = StringIO()
    metadata_buffer.write("cluster_id\tcluster_label\tauthor\tplatform\tdate\turl\tpreview\n")
    for idx in indices:
        row = frame.iloc[int(idx)]
        cluster_id = int(remapped_labels[int(idx)])
        metadata_buffer.write(
            "\t".join(
                [
                    str(cluster_id),
                    _sanitize_tsv(cluster_labels.get(cluster_id, f"Topic {cluster_id + 1}")),
                    _sanitize_tsv(row.get("author")),
                    _sanitize_tsv(row.get("platform")),
                    _sanitize_tsv(_format_value(row.get("date"))),
                    _sanitize_tsv(row.get("url")),
                    _sanitize_tsv(_truncate_text(row.get("text"), 180)),
                ]
            )
        )
        metadata_buffer.write("\n")

    message = None
    if len(indices) < len(frame):
        message = f"Export sampled {len(indices)} of {len(frame)} posts to keep Projector responsive."
    elif actual_clusters != safe_clusters:
        message = f"Requested {safe_clusters} clusters, but used {actual_clusters} for the available posts."

    return {
        "vectors_tsv": vectors_buffer.getvalue(),
        "metadata_tsv": metadata_buffer.getvalue(),
        "requested_clusters": safe_clusters,
        "actual_clusters": actual_clusters,
        "total_posts": len(frame),
        "exported_points": len(indices),
        "message": message,
    }


def _cluster_label_lookup(texts: list[str], labels: np.ndarray) -> dict[int, str]:
    cluster_texts: dict[int, list[str]] = defaultdict(list)
    for idx, label in enumerate(labels):
        cluster_texts[int(label)].append(texts[idx])

    mapping: dict[int, str] = {}
    for cluster_id, members in cluster_texts.items():
        keywords = _extract_keywords(members)
        mapping[cluster_id] = _build_label(cluster_id, keywords, [])
    return mapping


def _sample_indices(labels: np.ndarray, max_points: int) -> list[int]:
    total = len(labels)
    if total <= max_points:
        return list(range(total))

    rng = np.random.RandomState(42)
    grouped: dict[int, list[int]] = defaultdict(list)
    for idx, label in enumerate(labels):
        grouped[int(label)].append(idx)

    selected: list[int] = []
    for _, indices in sorted(grouped.items()):
        share = max(1, round(len(indices) / total * max_points))
        picked = rng.choice(indices, size=min(len(indices), share), replace=False)
        selected.extend(int(value) for value in picked)

    if len(selected) > max_points:
        selected = sorted(selected[:max_points])
    elif len(selected) < max_points:
        remaining = [idx for idx in range(total) if idx not in set(selected)]
        extra_needed = min(max_points - len(selected), len(remaining))
        if extra_needed > 0:
            extra = rng.choice(remaining, size=extra_needed, replace=False)
            selected.extend(int(value) for value in extra)

    return sorted(set(selected))


def _sanitize_tsv(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\t", " ").replace("\n", " ").strip()


def _format_value(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _truncate_text(value, limit: int) -> str:
    text = str(value or "").strip()
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."
