import re
from threading import Lock
from time import monotonic
from typing import Optional

from app.core.config import settings
from app.models.events_models import EventComparison, EventItem

GEMINI_API_KEYS = settings.GEMINI_API_KEYS
GEMINI_MODEL = "gemini-3-flash-preview"
_key_index = 0
_key_lock = Lock()
_key_backoff_until: dict[str, float] = {}
_global_backoff_until = 0.0


class GeminiTemporarilyUnavailable(Exception):
    pass


def _get_key_order() -> list[str]:
    if not GEMINI_API_KEYS:
        return []

    with _key_lock:
        if _global_backoff_until > monotonic():
            return []
        start = _key_index % len(GEMINI_API_KEYS)
        ordered = GEMINI_API_KEYS[start:] + GEMINI_API_KEYS[:start]
        now = monotonic()
        return [key for key in ordered if _key_backoff_until.get(key, 0.0) <= now]


def _peek_next_key() -> str | None:
    ordered = _get_key_order()
    return ordered[0] if ordered else None


def _peek_failover_key(current_key: str) -> str | None:
    ordered = _get_key_order()
    if not ordered:
        return None
    if current_key not in ordered:
        return ordered[0]
    current_index = ordered.index(current_key)
    next_index = current_index + 1
    if next_index < len(ordered):
        return ordered[next_index]
    return None


def _promote_key(key: str) -> None:
    global _key_index
    if not GEMINI_API_KEYS:
        return
    with _key_lock:
        if key in GEMINI_API_KEYS:
            _key_index = GEMINI_API_KEYS.index(key)


def _advance_past_key(key: str) -> None:
    global _key_index
    if not GEMINI_API_KEYS:
        return
    with _key_lock:
        if key in GEMINI_API_KEYS:
            _key_index = (GEMINI_API_KEYS.index(key) + 1) % len(GEMINI_API_KEYS)


def _is_retryable_gemini_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in {401, 403, 429, 500, 503}:
        return True

    message = str(exc).lower()
    retry_markers = (
        "quota",
        "rate limit",
        "resource exhausted",
        "too many requests",
        "429",
        "permission denied",
        "api key",
        "unauthenticated",
        "overloaded",
        "503",
    )
    return any(marker in message for marker in retry_markers)


def _is_quota_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        getattr(exc, "status_code", None) == 429
        or "quota" in message
        or "resource exhausted" in message
        or "resource_exhausted" in message
        or "rate limit" in message
        or "too many requests" in message
    )


def _extract_retry_delay_seconds(exc: Exception) -> float:
    message = str(exc)
    patterns = (
        r"retry in (\d+(?:\.\d+)?)s",
        r"'retryDelay': '(\d+(?:\.\d+)?)s'",
        r'"retryDelay": "(\d+(?:\.\d+)?)s"',
    )
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                return max(float(match.group(1)), 1.0)
            except ValueError:
                continue
    return 60.0


def _mark_key_backoff(key: str, seconds: float) -> None:
    with _key_lock:
        _key_backoff_until[key] = monotonic() + max(seconds, 1.0)


def _mark_global_backoff(seconds: float) -> None:
    global _global_backoff_until
    with _key_lock:
        _global_backoff_until = max(_global_backoff_until, monotonic() + max(seconds, 1.0))


async def _generate_with_rotation(contents: str) -> str:
    from google import genai

    current_key = _peek_next_key()
    if not current_key:
        raise GeminiTemporarilyUnavailable(
            "Gemini quota is cooling down, so requests are temporarily paused."
        )

    try:
        client = genai.Client(api_key=current_key)
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
        )
        _promote_key(current_key)
        return _extract_gemini_text(response)
    except Exception as exc:
        if not _is_retryable_gemini_error(exc):
            raise

        _advance_past_key(current_key)
        if _is_quota_error(exc):
            retry_after = _extract_retry_delay_seconds(exc)
            _mark_key_backoff(current_key, retry_after)
            print(
                f"[ai_summary] Gemini quota cooldown triggered for current key for ~{retry_after:.0f}s: {exc}"
            )
            raise GeminiTemporarilyUnavailable(str(exc)) from exc

        _mark_key_backoff(current_key, 300.0)
        print(f"[ai_summary] Gemini key failover triggered: {exc}")

        failover_key = _peek_failover_key(current_key)
        if not failover_key:
            raise GeminiTemporarilyUnavailable(
                "No Gemini API key is currently available."
            ) from exc

        try:
            client = genai.Client(api_key=failover_key)
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
            )
            _promote_key(failover_key)
            return _extract_gemini_text(response)
        except Exception as failover_exc:
            if _is_retryable_gemini_error(failover_exc):
                _advance_past_key(failover_key)
                if _is_quota_error(failover_exc):
                    retry_after = _extract_retry_delay_seconds(failover_exc)
                    _mark_key_backoff(failover_key, retry_after)
                    print(
                        f"[ai_summary] Gemini quota cooldown triggered for failover key for ~{retry_after:.0f}s: {failover_exc}"
                    )
                    raise GeminiTemporarilyUnavailable(str(failover_exc)) from failover_exc
                _mark_key_backoff(failover_key, 300.0)
            raise failover_exc


def _extract_gemini_text(response) -> str:
    candidates = getattr(response, "candidates", None) or []
    parts: list[str] = []

    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", None) or []:
            text = getattr(part, "text", None)
            if text and text.strip():
                parts.append(text.strip())

    if parts:
        return "\n".join(parts).strip()

    direct_text = getattr(response, "text", None)
    return (direct_text or "").strip()


def _fallback_summary(context: str, reason: str | None = None) -> str:
    lines = [l.strip() for l in context.split("\n") if l.strip()]
    if not lines:
        return "No data available for summary generation."

    message = f"This analysis covers {len(lines)} data points."
    if reason:
        return f"{message} {reason}"
    return (
        f"{message} AI-generated plain-language summaries are currently unavailable."
    )


def _fallback_reason_for_exception(exc: Exception) -> str:
    message = str(exc).lower()
    if (
        "cooling down" in message
        or "quota" in message
        or "resource_exhausted" in message
        or "429" in message
    ):
        return "Gemini quota is currently exhausted, so a rule-based summary is being shown instead."
    if "api key" in message or "unauthenticated" in message or "permission denied" in message:
        return "Gemini authentication failed, so a rule-based summary is being shown instead."
    return "Gemini is currently unavailable, so a rule-based summary is being shown instead."


async def generate_summary(
    context: str,
    prompt_template: str = "Summarize the following data trend for a non-technical audience in 2-3 sentences:\n\n{context}",
) -> str:
    if not GEMINI_API_KEYS:
        return _fallback_summary(
            context,
            "No Gemini API key is configured, so a rule-based summary is being shown instead.",
        )

    try:
        text = await _generate_with_rotation(
            (
                "You are a data analyst writing brief, clear summaries of social media trends "
                "for non-technical readers.\n\n"
                f"{prompt_template.format(context=context)}"
            )
        )
        return text or _fallback_summary(context)
    except Exception as e:
        print(f"[ai_summary] LLM call failed: {e}")
        return _fallback_summary(context, _fallback_reason_for_exception(e))


async def generate_related_queries(query: str) -> list[str]:
    if not GEMINI_API_KEYS:
        return []

    try:
        import json

        text = await _generate_with_rotation(
            (
                "Given a search query about social media narratives, suggest exactly 3 related "
                "search queries. Return ONLY a JSON array of 3 strings.\n\n"
                f'Query: "{query}"'
            )
        )
        return json.loads(text)
    except Exception:
        return []
def build_timeseries_context(
    buckets: list[dict],
    query: str,
    granularity: str,
    total_posts: int,
    group_by: str | None = None,
    grouped: list[dict] | None = None,
    selected_event: EventItem | None = None,
    event_comparison: EventComparison | None = None,
) -> str:
    parts: list[str] = []

    label = f'for query "{query}"' if query else "across all posts"
    parts.append(f"Time-series analysis {label} (bucketed by {granularity}).")
    parts.append(f"Total posts: {total_posts}.")

    if buckets:
        counts = [b["count"] for b in buckets]
        parts.append(f"Date range: {buckets[0]['date']} to {buckets[-1]['date']}.")
        parts.append(f"Peak: {max(counts)} posts, Low: {min(counts)} posts.")
        if len(set(counts)) <= 1:
            parts.append("Trend shape: flat.")
        zero_pct = counts.count(0) / max(len(counts), 1)
        if zero_pct > 0.6:
            parts.append(f"Sparsity: {int(zero_pct * 100)}% of buckets had zero posts.")
        if total_posts <= 3:
            parts.append("Sample size: tiny result set.")
    elif grouped:
        parts.append(f"Grouped by: {group_by}.")
        for g in grouped[:5]:
            g_counts = [b["count"] for b in g["buckets"]] if g["buckets"] else [0]
            parts.append(
                f"  • {g['group']}: {sum(g_counts)} total posts, "
                f"peak {max(g_counts)}, {len(g['buckets'])} buckets."
            )

    if buckets:
        tail = buckets[-15:]
        parts.append("\nRecent data:")
        for b in tail:
            parts.append(f"  {b['date']}: {b['count']} posts")

    if selected_event:
        parts.append("\nSelected event overlay:")
        parts.append(f"  Event: {selected_event.title}")
        parts.append(f"  Date: {selected_event.date}")
        if selected_event.category:
            parts.append(f"  Category: {selected_event.category}")
        if selected_event.description:
            parts.append(f"  Description: {selected_event.description}")

        if event_comparison:
            ratio = (
                f"{event_comparison.change_ratio * 100:.1f}%"
                if event_comparison.change_ratio is not None
                else "n/a"
            )
            parts.append(
                "  Before/after comparison: "
                f"{event_comparison.before_total} posts in the {event_comparison.window_buckets} buckets before, "
                f"{event_comparison.after_total} posts in the {event_comparison.window_buckets} buckets after, "
                f"delta {event_comparison.delta}, change ratio {ratio}."
            )
        else:
            parts.append(
                "  Comparison note: the selected event does not align cleanly with the returned buckets."
            )

    return "\n".join(parts)


def build_timeseries_fallback(
    buckets: list[dict],
    query: str,
    granularity: str,
    total_posts: int,
    group_by: str | None = None,
    grouped: list[dict] | None = None,
    selected_event: EventItem | None = None,
    event_comparison: EventComparison | None = None,
) -> str:
    if not buckets and not grouped:
        return "No time-series data to summarise."

    label = f'for "{query}"' if query else ""
    event_note = ""
    if selected_event and event_comparison:
        direction = "little net change around"
        if event_comparison.delta > 0:
            direction = "higher activity after"
        elif event_comparison.delta < 0:
            direction = "lower activity after"
        ratio_note = (
            f", a {event_comparison.change_ratio * 100:.1f}% change"
            if event_comparison.change_ratio is not None
            else ""
        )
        event_note = (
            f" Around the selected event, {selected_event.title} on {selected_event.date}, there was "
            f"{direction}: {event_comparison.before_total} posts in the {event_comparison.window_buckets} buckets before "
            f"versus {event_comparison.after_total} after ({event_comparison.delta:+d}{ratio_note})."
        )
    elif selected_event:
        event_note = (
            f" The selected event, {selected_event.title} on {selected_event.date}, is shown as an overlay, "
            "but it does not line up with enough buckets for a before/after comparison."
        )

    if buckets:
        counts = [b["count"] for b in buckets]
        peak_idx = counts.index(max(counts))
        peak_date = buckets[peak_idx]["date"]
        peak_val = counts[peak_idx]
        if total_posts <= 3 or len(buckets) <= 2:
            return (
                f"There are only {total_posts} matching posts {label}, so this trend should be treated as a tiny sample. "
                f"The visible peak is {peak_val} posts on {peak_date}."
                f"{event_note}"
            )

        if len(set(counts)) <= 1:
            return (
                f"Across {len(buckets)} {granularity}s {label}, activity was essentially flat at about {peak_val} posts per bucket. "
                f"There were {total_posts} total matching posts in the returned range."
                f"{event_note}"
            )

        mid = len(counts) // 2
        first_avg = sum(counts[:mid]) / max(mid, 1)
        second_avg = sum(counts[mid:]) / max(len(counts) - mid, 1)
        if second_avg > first_avg * 1.2:
            trend = "an upward trend"
        elif second_avg < first_avg * 0.8:
            trend = "a downward trend"
        else:
            trend = "a relatively flat pattern"

        zero_pct = counts.count(0) / max(len(counts), 1)
        sparse_note = ""
        if zero_pct > 0.6:
            sparse_note = (
                f" Note: {int(zero_pct * 100)}% of {granularity}s had zero posts, "
                "indicating sparse activity."
            )

        return (
            f"Over {len(buckets)} {granularity}s {label}, there were "
            f"{total_posts} total posts showing {trend}. "
            f"The peak was {peak_val} posts on {peak_date}."
            f"{sparse_note}"
            f"{event_note}"
        )

    if grouped:
        sorted_groups = sorted(
            grouped, key=lambda g: sum(b["count"] for b in g["buckets"]), reverse=True
        )
        top = sorted_groups[:3]
        top_str = ", ".join(
            f"{g['group']} ({sum(b['count'] for b in g['buckets'])} posts)"
            for g in top
        )
        return (
            f"Grouped by {group_by} {label}: {len(grouped)} groups found. "
            f"Top contributors: {top_str}."
            f"{event_note}"
        )

    return "Summary could not be generated from the available data."


async def generate_timeseries_summary(
    *,
    buckets: list[dict],
    query: str,
    granularity: str,
    total_posts: int,
    group_by: str | None = None,
    grouped: list[dict] | None = None,
    selected_event: EventItem | None = None,
    event_comparison: EventComparison | None = None,
) -> tuple[str, str]:
    context = build_timeseries_context(
        buckets=buckets,
        query=query,
        granularity=granularity,
        total_posts=total_posts,
        group_by=group_by,
        grouped=grouped,
        selected_event=selected_event,
        event_comparison=event_comparison,
    )
    if not context.strip():
        return "No time-series data to summarise.", "fallback-empty"

    fallback_summary = build_timeseries_fallback(
        buckets=buckets,
        query=query,
        granularity=granularity,
        total_posts=total_posts,
        group_by=group_by,
        grouped=grouped,
        selected_event=selected_event,
        event_comparison=event_comparison,
    )

    if not GEMINI_API_KEYS:
        return (
            (
                f"{fallback_summary} "
                "No Gemini API key is configured, so a rule-based summary is being shown instead."
            ),
            "fallback-rule-based-no-key",
        )

    try:
        summary = await _generate_with_rotation(
            (
                "You are a data analyst writing brief, clear summaries of social media trends "
                "for non-technical readers.\n"
                "When a selected event overlay is present, explicitly say whether activity increased, decreased, "
                "or showed no clear change around that event using the provided before/after comparison. "
                "Do not give a generic summary that could apply to every event.\n\n"
                "Summarize the following data trend for a non-technical audience in 2-3 sentences:\n\n"
                f"{context}"
            )
        )
        return (summary or fallback_summary), "llm"
    except Exception as exc:
        print(f"[ai_summary] Timeseries LLM call failed: {exc}")
        return (
            f"{fallback_summary} {_fallback_reason_for_exception(exc)}",
            "fallback-rule-based-llm-unavailable",
        )
