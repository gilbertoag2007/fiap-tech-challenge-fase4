from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controller.sinais_vitais_controller import roteador as roteador_sinais_vitais
from controller.fisioterapia_controller import roteador as roteador_fisioterapia
from fisioterapia.config import root_path
from fisioterapia.jobs import AnalysisService


def create_app(fisioterapia_service: AnalysisService | None = None) -> FastAPI:
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
    application.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type", "Range"],
    )
    application.include_router(roteador_sinais_vitais)
    application.include_router(roteador_fisioterapia)
    return application


app = create_app()
