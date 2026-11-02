from fastapi import FastAPI

from controller.sinais_vitais_controller import roteador as roteador_sinais_vitais

app = FastAPI(
    title="analise-medica-api",
    description="API para processamento de dados clínicos.",
    version="0.1.0",
)

app.include_router(roteador_sinais_vitais)
