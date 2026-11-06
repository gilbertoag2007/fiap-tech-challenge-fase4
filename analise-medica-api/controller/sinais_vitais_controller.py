from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from integrations.integracao_physionet import ErroRegistroExterno
from services.sinais_vitais_service import (
    GraficosNaoLocalizadosError,
    PacienteNaoLocalizadoError,
    RelatorioNaoLocalizadoError,
    SinaisVitaisDetalhadosNaoLocalizadosError,
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


@roteador.get("/tabela-referencia")
def recuperar_tabela_referencia(
    sinal: str | None = Query(default=None),
) -> dict[str, Any]:
    servico = _criar_servico()
    if sinal is None or not sinal.strip():
        return {"sinais_vitais": servico.listar_tabelas_referencia()}

    try:
        tabela = servico.recuperar_tabela_referencia(sinal)
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail="Tabela de referência não localizada para o sinal informado.",
        ) from error

    return {
        "sinal": sinal.strip(),
        "tabela": tabela,
    }


@roteador.get("/relatorio")
def recuperar_relatorio(
    cpf: str | None = Query(default=None),
    id_registro: str | None = Query(default=None, alias="id"),
) -> dict[str, Any]:
    cpf = cpf.strip() if cpf and cpf.strip() else None
    id_registro = (
        id_registro.strip() if id_registro and id_registro.strip() else None
    )
    if cpf is None and id_registro is None:
        raise HTTPException(
            status_code=422,
            detail="Informe ao menos um dos parâmetros: cpf ou id.",
        )

    try:
        return _criar_servico().recuperar_relatorio(cpf, id_registro)
    except RelatorioNaoLocalizadoError as error:
        raise HTTPException(
            status_code=404,
            detail="Relatório não localizado.",
        ) from error


@roteador.get("/graficos")
def recuperar_graficos(
    cpf: str | None = Query(default=None),
    id_registro: str | None = Query(default=None, alias="id"),
) -> Response:
    cpf = cpf.strip() if cpf and cpf.strip() else None
    id_registro = (
        id_registro.strip() if id_registro and id_registro.strip() else None
    )
    if cpf is None and id_registro is None:
        raise HTTPException(
            status_code=422,
            detail="Informe ao menos um dos parâmetros: cpf ou id.",
        )

    try:
        conteudo_zip, nome_arquivo = _criar_servico().recuperar_graficos_zip(
            cpf,
            id_registro,
        )
    except GraficosNaoLocalizadosError as error:
        raise HTTPException(
            status_code=404,
            detail="Gráficos não localizados para o paciente informado.",
        ) from error

    return Response(
        content=conteudo_zip,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@roteador.get("/datalhamento")
def recuperar_sinais_vitais_detalhados(
    cpf: str | None = Query(default=None),
    id_registro: str | None = Query(default=None, alias="id"),
) -> FileResponse:
    cpf = cpf.strip() if cpf and cpf.strip() else None
    id_registro = (
        id_registro.strip() if id_registro and id_registro.strip() else None
    )
    if cpf is None and id_registro is None:
        raise HTTPException(
            status_code=422,
            detail="Informe ao menos um dos parâmetros: cpf ou id.",
        )

    try:
        caminho_csv = _criar_servico().recuperar_csv(
            cpf,
            id_registro,
        )
    except SinaisVitaisDetalhadosNaoLocalizadosError as error:
        raise HTTPException(
            status_code=404,
            detail=(
                "Arquivo detalhado com os sinais vitais do paciente "
                "selecionado não foi localizado."
            ),
        ) from error

    return FileResponse(
        path=caminho_csv,
        media_type="text/csv",
        filename=caminho_csv.name,
    )


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
