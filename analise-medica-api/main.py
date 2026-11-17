from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app(fisioterapia_service=None) -> FastAPI:
    if os.getenv("DEMO_MODE", "").lower() in {"1", "true", "yes"}:
        from demo_app import create_demo_app
        application = create_demo_app()
        configure_cors(application)
        return application

    from controller.sinais_vitais_controller import roteador as roteador_sinais_vitais
    from controller.fisioterapia_controller import roteador as roteador_fisioterapia
    from fisioterapia.config import root_path
    from fisioterapia.jobs import AnalysisService

    @asynccontextmanager
    async def lifespan(application):
        application.state.fisioterapia = fisioterapia_service or AnalysisService(root_path())
        try:
            yield
        finally:
            application.state.fisioterapia.close()

    application = FastAPI(
        title="analise-medica-api",
        description="API para processamento de sinais vitais e vídeos de fisioterapia.",
        version="0.2.0",
        lifespan=lifespan,
    )
    configure_cors(application)

    @application.get("/health")
    def health():
        return {"status": "ok", "mode": "full"}

    application.include_router(roteador_sinais_vitais)
    application.include_router(roteador_fisioterapia)
    return application


def configure_cors(application):
    origins = [origin.strip().rstrip('/') for origin in os.getenv("FRONTEND_ORIGINS", "").split(',') if origin.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type", "Range"],
    )


app = create_app()
