import os
from dotenv import load_dotenv

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(_BACKEND_ROOT, ".env"))


def _split_csv_env(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _collect_gemini_keys() -> list[str]:
    keys: list[str] = []

    keys.extend(_split_csv_env(os.getenv("GEMINI_API_KEYS")))

    primary = os.getenv("GEMINI_API_KEY")
    if primary and primary.strip():
        keys.append(primary.strip())

    for index in range(1, 6):
        key = os.getenv(f"GEMINI_API_KEY_{index}")
        if key and key.strip():
            keys.append(key.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


class Settings:
    PROJECT_NAME: str = "EchoMatrix API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DATA_DIR: str = os.path.join(_BACKEND_ROOT, "data")
    CACHE_DIR: str = os.path.join(DATA_DIR, ".cache")
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    GEMINI_API_KEYS: list[str] = _collect_gemini_keys()
    GEMINI_API_KEY: str | None = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else None
    ALLOWED_ORIGINS: list[str] = _split_csv_env(os.getenv("ALLOWED_ORIGINS")) or [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


settings = Settings()
