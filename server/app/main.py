"""FastAPI application entrypoint for SynthX.AI backend."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import datasets, health, schema, stats
from app.core.config import get_settings
from app.core.events import register_event_handlers
from app.core.logging import configure_logging
from app.core.tracing import configure_tracing

configure_logging()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_tracing(settings)
    app = FastAPI(title=settings.app_name, version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=settings.api_v1_prefix)
    app.include_router(schema.router, prefix=settings.api_v1_prefix)
    app.include_router(datasets.router, prefix=settings.api_v1_prefix)
    app.include_router(stats.router, prefix=settings.api_v1_prefix)

    register_event_handlers(app)

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {"message": f"{settings.app_name} backend is running"}

    return app


app = create_app()
