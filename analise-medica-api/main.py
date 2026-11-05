from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controller.sinais_vitais_controller import roteador as roteador_sinais_vitais

app = FastAPI(
    title="analise-medica-api",
    description="API para processamento de dados clínicos.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["GET"],
    allow_headers=["Accept"],
)

app.include_router(roteador_sinais_vitais)
