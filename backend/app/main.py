from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.routers import search, timeseries, topics, network, stats, events, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.data_loader import get_dataset_repository, load_data
    from app.services.embeddings import get_provider
    from app.routers.dashboard import warm_dashboard_overview_cache
    print("[EchoMatrix] Loading dataset...")
    repo = get_dataset_repository()
    df = load_data()
    print(f"[EchoMatrix] Loaded {len(df)} records.")
    print(f"[EchoMatrix] Dataset cache: {'hit' if repo.stats.cached else 'miss'}")
    if not df.empty:
        print("[EchoMatrix] Warming embedding cache...")
        get_provider().warm_cache(df["text"].tolist())
        print("[EchoMatrix] Embedding cache ready.")
        try:
            print("[EchoMatrix] Warming dashboard overview cache...")
            warm_dashboard_overview_cache(force_refresh=True)
            print("[EchoMatrix] Dashboard overview cache ready.")
        except Exception as exc:
            print(f"[EchoMatrix] Dashboard overview warm-up skipped: {exc}")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.include_router(search.router, prefix=settings.API_PREFIX, tags=["search"])
    app.include_router(timeseries.router, prefix=settings.API_PREFIX, tags=["timeseries"])
    app.include_router(topics.router, prefix=settings.API_PREFIX, tags=["topics"])
    app.include_router(network.router, prefix=settings.API_PREFIX, tags=["network"])
    app.include_router(stats.router, prefix=settings.API_PREFIX, tags=["stats"])
    app.include_router(events.router, prefix=settings.API_PREFIX, tags=["events"])
    app.include_router(dashboard.router, prefix=settings.API_PREFIX, tags=["dashboard"])

    @app.get("/")
    def root():
        return {"message": "EchoMatrix API", "version": settings.VERSION}

    @app.get("/health")
    def health():
        from app.services.data_loader import get_dataset_repository, load_data
        repo = get_dataset_repository()
        df = load_data()
        return {
            "status": "ok",
            "records": len(df),
            "cache_used": repo.stats.cached,
            "issues": len(repo.issues),
        }

    @app.post("/dev/reload-data")
    def reload_data_dev():
        from app.services.data_loader import reload_data

        repo = reload_data()
        return {
            "status": "reloaded",
            "records": len(repo.records),
            "issues": len(repo.issues),
            "cached": repo.stats.cached,
            "cache_path": repo.stats.cache_path,
        }

    return app


app = create_app()
