from __future__ import annotations

import json
import pickle
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlparse

import pandas as pd

from app.core.config import settings

DATASET_FILENAME = "data.jsonl"
CACHE_VERSION = 1
HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_]+)")
URL_RE = re.compile(r"https?://[^\s)]+", re.IGNORECASE)
THUMBNAIL_SENTINELS = {"self", "default", "image", "nsfw", "spoiler", "default", ""}


@dataclass(slots=True)
class LoaderIssue:
    line_number: int
    code: str
    message: str


@dataclass(slots=True)
class DatasetStats:
    source_path: str
    total_lines: int
    valid_records: int
    skipped_records: int
    malformed_json_rows: int
    invalid_shape_rows: int
    incomplete_rows: int
    cached: bool
    cache_path: str
    loaded_at: str


class DatasetRepository:
    def __init__(
        self,
        *,
        records: list[dict[str, Any]],
        issues: list[LoaderIssue],
        stats: DatasetStats,
    ) -> None:
        self.records = records
        self.issues = issues
        self.stats = stats
        self._frame = pd.DataFrame.from_records(records) if records else _empty_frame()
        if not self._frame.empty and "date" in self._frame.columns:
            self._frame["date"] = pd.to_datetime(self._frame["date"], errors="coerce", utc=True)

    @property
    def frame(self) -> pd.DataFrame:
        return self._frame

    def to_dataframe(self) -> pd.DataFrame:
        return self._frame

    def sample_record(self) -> dict[str, Any] | None:
        if not self.records:
            return None
        return self.records[0]

    def summary(self) -> dict[str, Any]:
        return {
            "records": len(self.records),
            "issues": len(self.issues),
            "source_path": self.stats.source_path,
            "cached": self.stats.cached,
            "cache_path": self.stats.cache_path,
        }


_repo: DatasetRepository | None = None
_lock = Lock()


def get_dataset_repository(force: bool = False) -> DatasetRepository:
    global _repo
    with _lock:
        if _repo is None or force:
            _repo = _load_repository(force=force)
        return _repo


def load_data(force: bool = False) -> pd.DataFrame:
    return get_dataset_repository(force=force).to_dataframe()


def reload_data() -> DatasetRepository:
    return get_dataset_repository(force=True)


def get_normalized_record_example() -> dict[str, Any] | None:
    return get_dataset_repository().sample_record()


def _load_repository(force: bool = False) -> DatasetRepository:
    source_path = Path(settings.DATA_DIR) / DATASET_FILENAME
    cache_path = Path(settings.CACHE_DIR) / "data_loader.cache.pkl"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if not source_path.exists():
        return DatasetRepository(
            records=[],
            issues=[],
            stats=DatasetStats(
                source_path=str(source_path),
                total_lines=0,
                valid_records=0,
                skipped_records=0,
                malformed_json_rows=0,
                invalid_shape_rows=0,
                incomplete_rows=0,
                cached=False,
                cache_path=str(cache_path),
                loaded_at=_utc_now(),
            ),
        )

    signature = _source_signature(source_path)
    if not force:
        cached = _read_cache(cache_path, signature)
        if cached is not None:
            return cached

    records: list[dict[str, Any]] = []
    issues: list[LoaderIssue] = []
    malformed_json_rows = 0
    invalid_shape_rows = 0
    incomplete_rows = 0
    total_lines = 0

    with source_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            total_lines += 1
            line = raw_line.strip()
            if not line:
                issues.append(LoaderIssue(line_number, "empty_line", "Skipping empty line."))
                continue

            try:
                root = json.loads(line)
            except json.JSONDecodeError as exc:
                malformed_json_rows += 1
                issues.append(LoaderIssue(line_number, "malformed_json", f"JSON parse failed: {exc.msg}"))
                continue

            raw_post = _unwrap_post(root)
            if raw_post is None:
                invalid_shape_rows += 1
                issues.append(LoaderIssue(line_number, "invalid_shape", "Row was not a Reddit t3/data object or flat dict."))
                continue

            normalized, warnings = _normalize_record(raw_post, root, line_number)
            if normalized is None:
                invalid_shape_rows += 1
                issues.extend(warnings)
                continue

            if warnings:
                incomplete_rows += 1
                issues.extend(warnings)

            records.append(normalized)

    stats = DatasetStats(
        source_path=str(source_path),
        total_lines=total_lines,
        valid_records=len(records),
        skipped_records=max(total_lines - len(records), 0),
        malformed_json_rows=malformed_json_rows,
        invalid_shape_rows=invalid_shape_rows,
        incomplete_rows=incomplete_rows,
        cached=False,
        cache_path=str(cache_path),
        loaded_at=_utc_now(),
    )

    repository = DatasetRepository(records=records, issues=issues, stats=stats)
    _write_cache(cache_path, signature, records, issues, stats)
    return repository


def _normalize_record(
    raw_post: dict[str, Any],
    raw_root: dict[str, Any],
    line_number: int,
) -> tuple[dict[str, Any] | None, list[LoaderIssue]]:
    issues: list[LoaderIssue] = []
    if not isinstance(raw_post, dict):
        issues.append(LoaderIssue(line_number, "invalid_data", "The `data` payload was not an object."))
        return None, issues

    title = _clean_text(raw_post.get("title"))
    body_text = _clean_text(raw_post.get("selftext"))
    full_text = "\n\n".join(part for part in (title, body_text) if part).strip()
    if not full_text:
        issues.append(LoaderIssue(line_number, "empty_text", "Skipping row because both title and selftext were empty."))
        return None, issues

    post_id = _clean_optional(raw_post.get("id"))
    if not post_id:
        issues.append(LoaderIssue(line_number, "missing_id", "Skipping row because `data.id` was missing."))
        return None, issues

    created_at = _timestamp_to_iso(raw_post.get("created_utc"))
    if created_at is None:
        issues.append(LoaderIssue(line_number, "missing_created_utc", "Record is missing a valid created_utc timestamp."))

    author = _clean_optional(raw_post.get("author"))
    if not author:
        issues.append(LoaderIssue(line_number, "missing_author", "Record is missing author; using placeholder."))
        author = "[unknown]"

    subreddit = _clean_optional(raw_post.get("subreddit"))
    if not subreddit:
        issues.append(LoaderIssue(line_number, "missing_subreddit", "Record is missing subreddit; using placeholder."))
        subreddit = "unknown"

    permalink = _build_permalink(raw_post.get("permalink"))
    canonical_url = _canonical_url(raw_post.get("url"), permalink, bool(raw_post.get("is_self")))
    domain = _normalize_domain(raw_post.get("domain"))
    hashtags = _extract_hashtags(full_text)
    links = _extract_links(full_text, canonical_url)
    preview_image_url = _preview_image_url(raw_post.get("preview"))
    thumbnail_url = _thumbnail_url(raw_post.get("thumbnail"))
    media_type = _media_type(raw_post, canonical_url, preview_image_url)
    edited_at = _edited_to_iso(raw_post.get("edited"))

    normalized = {
        "text": full_text,
        "author": author,
        "date": created_at,
        "url": canonical_url,
        "hashtags": hashtags,
        "platform": f"r/{subreddit}",
        "post_id": post_id,
        "platform_name": "reddit",
        "source_kind": str(raw_root.get("kind") or "t3"),
        "platform_item_id": _clean_optional(raw_post.get("name")),
        "created_at": created_at,
        "edited_at": edited_at,
        "title": title,
        "body_text": body_text or None,
        "full_text": full_text,
        "permalink_url": permalink,
        "canonical_url": canonical_url,
        "domain": domain,
        "is_self_post": bool(raw_post.get("is_self")),
        "subreddit_id": _clean_optional(raw_post.get("subreddit_id")),
        "subreddit_name": subreddit,
        "subreddit_label": _clean_optional(raw_post.get("subreddit_name_prefixed")) or f"r/{subreddit}",
        "subreddit_type": _clean_optional(raw_post.get("subreddit_type")),
        "author_id": _clean_optional(raw_post.get("author_fullname")),
        "author_username": author,
        "author_flair_text": _clean_optional(raw_post.get("author_flair_text")),
        "author_flair_type": _clean_optional(raw_post.get("author_flair_type")),
        "link_flair_text": _clean_optional(raw_post.get("link_flair_text")),
        "link_flair_type": _clean_optional(raw_post.get("link_flair_type")),
        "score": _safe_int(raw_post.get("score")),
        "upvotes": _safe_int(raw_post.get("ups")),
        "downvotes": _safe_int(raw_post.get("downs")),
        "upvote_ratio": _safe_float(raw_post.get("upvote_ratio")),
        "comment_count": _safe_int(raw_post.get("num_comments")),
        "award_count": _safe_int(raw_post.get("total_awards_received")),
        "is_nsfw": bool(raw_post.get("over_18")),
        "is_spoiler": bool(raw_post.get("spoiler")),
        "is_locked": bool(raw_post.get("locked")),
        "is_stickied": bool(raw_post.get("stickied")),
        "is_pinned": bool(raw_post.get("pinned")),
        "is_archived": bool(raw_post.get("archived")),
        "preview_image_url": preview_image_url,
        "thumbnail_url": thumbnail_url,
        "media_type": media_type,
        "has_external_url": _has_external_url(canonical_url, permalink, bool(raw_post.get("is_self"))),
        "links": links,
        "entities": [],
        "language": None,
        "metadata": {
            "raw_kind": raw_root.get("kind"),
            "crosspost_parent_id": _clean_optional(raw_post.get("crosspost_parent")),
            "has_preview": bool(raw_post.get("preview")),
            "has_media": bool(raw_post.get("media") or raw_post.get("secure_media")),
            "has_gallery": bool(raw_post.get("gallery_data")),
            "is_video": bool(raw_post.get("is_video")),
            "is_gallery": bool(raw_post.get("is_gallery")),
            "is_reddit_media_domain": bool(raw_post.get("is_reddit_media_domain")),
        },
        "raw_root": raw_root,
        "raw_post": raw_post,
    }
    return normalized, issues


def _unwrap_post(root: Any) -> dict[str, Any] | None:
    if not isinstance(root, dict):
        return None
    if isinstance(root.get("data"), dict):
        return root["data"]
    if "id" in root or "title" in root:
        return root
    return None


def _source_signature(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
        "cache_version": CACHE_VERSION,
    }


def _read_cache(path: Path, signature: dict[str, Any]) -> DatasetRepository | None:
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            payload = pickle.load(handle)
    except Exception:
        return None

    if not isinstance(payload, dict) or payload.get("signature") != signature:
        return None

    stats_payload = payload.get("stats", {})
    stats = DatasetStats(
        source_path=stats_payload.get("source_path", signature["path"]),
        total_lines=int(stats_payload.get("total_lines", 0)),
        valid_records=int(stats_payload.get("valid_records", 0)),
        skipped_records=int(stats_payload.get("skipped_records", 0)),
        malformed_json_rows=int(stats_payload.get("malformed_json_rows", 0)),
        invalid_shape_rows=int(stats_payload.get("invalid_shape_rows", 0)),
        incomplete_rows=int(stats_payload.get("incomplete_rows", 0)),
        cached=True,
        cache_path=str(path),
        loaded_at=_utc_now(),
    )
    issues = [
        LoaderIssue(
            line_number=int(issue.get("line_number", 0)),
            code=str(issue.get("code", "cached_issue")),
            message=str(issue.get("message", "")),
        )
        for issue in payload.get("issues", [])
        if isinstance(issue, dict)
    ]
    return DatasetRepository(
        records=list(payload.get("records", [])),
        issues=issues,
        stats=stats,
    )


def _write_cache(
    path: Path,
    signature: dict[str, Any],
    records: list[dict[str, Any]],
    issues: list[LoaderIssue],
    stats: DatasetStats,
) -> None:
    payload = {
        "signature": signature,
        "records": records,
        "issues": [
            {"line_number": issue.line_number, "code": issue.code, "message": issue.message}
            for issue in issues
        ],
        "stats": {
            "source_path": stats.source_path,
            "total_lines": stats.total_lines,
            "valid_records": stats.valid_records,
            "skipped_records": stats.skipped_records,
            "malformed_json_rows": stats.malformed_json_rows,
            "invalid_shape_rows": stats.invalid_shape_rows,
            "incomplete_rows": stats.incomplete_rows,
        },
    }
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp_path.open("wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
        tmp_path.replace(path)
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "text",
            "author",
            "date",
            "url",
            "hashtags",
            "platform",
            "post_id",
            "title",
            "body_text",
            "full_text",
            "subreddit_name",
            "score",
            "comment_count",
            "raw_post",
        ]
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").strip()


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _timestamp_to_iso(value: Any) -> str | None:
    number = _safe_float(value)
    if number is None:
        return None
    try:
        return datetime.fromtimestamp(number, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _edited_to_iso(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    return _timestamp_to_iso(value)


def _build_permalink(value: Any) -> str:
    raw = _clean_optional(value)
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if not raw.startswith("/"):
        raw = f"/{raw}"
    return f"https://www.reddit.com{raw}"


def _canonical_url(raw_url: Any, permalink_url: str, is_self_post: bool) -> str:
    url = _clean_optional(raw_url)
    if not url:
        return permalink_url
    if is_self_post:
        return permalink_url or url
    return url


def _normalize_domain(value: Any) -> str | None:
    domain = _clean_optional(value)
    if not domain:
        return None
    return domain.lower()


def _preview_image_url(preview: Any) -> str | None:
    if not isinstance(preview, dict):
        return None
    images = preview.get("images")
    if not isinstance(images, list) or not images:
        return None
    first = images[0]
    if not isinstance(first, dict):
        return None
    source = first.get("source")
    if not isinstance(source, dict):
        return None
    return _clean_optional(source.get("url"))


def _thumbnail_url(thumbnail: Any) -> str | None:
    value = _clean_optional(thumbnail)
    if not value:
        return None
    if value.lower() in THUMBNAIL_SENTINELS:
        return None
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return None


def _media_type(raw_post: dict[str, Any], canonical_url: str, preview_image_url: str | None) -> str | None:
    if bool(raw_post.get("is_self")):
        return "self"
    if bool(raw_post.get("gallery_data")) or bool(raw_post.get("is_gallery")):
        return "gallery"
    domain = _normalize_domain(raw_post.get("domain")) or ""
    if bool(raw_post.get("is_video")) or domain == "v.redd.it":
        return "video"
    if domain in {"youtube.com", "youtu.be"}:
        return "youtube"
    if preview_image_url or domain == "i.redd.it":
        return "image"
    if canonical_url:
        return "link"
    return None


def _extract_hashtags(text: str) -> list[str]:
    return sorted({match.group(1).lower() for match in HASHTAG_RE.finditer(text or "")})


def _extract_links(text: str, canonical_url: str) -> list[dict[str, str | None]]:
    urls = {_clean_optional(match.group(0)) for match in URL_RE.finditer(text or "")}
    if canonical_url:
        urls.add(canonical_url)
    links: list[dict[str, str | None]] = []
    for url in sorted(item for item in urls if item):
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "") or None
            path = parsed.path or None
        except ValueError:
            domain = None
            path = None
        links.append(
            {
                "url": url,
                "domain": domain,
                "path": path,
            }
        )
    return links


def _has_external_url(canonical_url: str, permalink_url: str, is_self_post: bool) -> bool:
    if not canonical_url:
        return False
    if is_self_post:
        return False
    return canonical_url != permalink_url


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
