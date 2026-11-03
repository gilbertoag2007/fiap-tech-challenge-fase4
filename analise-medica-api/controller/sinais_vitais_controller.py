from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from integrations.integracao_physionet import ErroRegistroExterno
from services.sinais_vitais_service import (
    PacienteNaoLocalizadoError,
    ServicoSinaisVitais,
)


class RequisicaoSinaisVitais(BaseModel):
    id: str


class PacienteResponse(BaseModel):
    id: str
    cpf: str
    nome: str
    idade: int
    genero: str
    prontuario: str


roteador = APIRouter(prefix="/v1/sinais-vitais", tags=["Sinais vitais"])


def _criar_servico() -> ServicoSinaisVitais:
    diretorio_api = Path(__file__).resolve().parents[1]
    return ServicoSinaisVitais(
        caminho_catalogo_pacientes=diretorio_api / "data" / "pacientes.json",
        diretorio_saida=diretorio_api / "data",
    )


@roteador.get("/paciente", response_model=list[PacienteResponse])
def listar_pacientes() -> list[dict[str, Any]]:
    return _criar_servico().listar_pacientes()


@roteador.post("/")
def baixar_sinais_vitais(requisicao: RequisicaoSinaisVitais) -> dict[str, Any]:
    servico = _criar_servico()
    try:
        return servico.baixar_dados_paciente(requisicao.id)
    except PacienteNaoLocalizadoError as error:
        raise HTTPException(status_code=404, detail="Paciente não localizado") from error
    except ErroRegistroExterno as error:
        raise HTTPException(
            status_code=502,
            detail=f"Não foi possível baixar os dados do PhysioNet: {error}",
        ) from error
