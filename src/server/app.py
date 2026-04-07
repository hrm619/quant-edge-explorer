"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import get_settings
from server.routers import artifacts, chat, conversations


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Quant-Edge Explorer",
        version="0.1.0",
        description="Conversational research agent API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(artifacts.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
