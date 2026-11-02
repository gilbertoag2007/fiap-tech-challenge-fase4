import json
from pathlib import Path
from typing import Any

from integrations.gerador_graficos import GeradorGraficos
from integrations.integracao_physionet import IntegracaoPhysioNet
from services.gerador_relatorios import GeradorRelatorios


class PacienteNaoLocalizadoError(Exception):
    pass


class ServicoSinaisVitais:
    def __init__(
        self,
        caminho_catalogo_pacientes: str | Path,
        diretorio_saida: str | Path,
        integracao: IntegracaoPhysioNet | None = None,
    ) -> None:
        self.caminho_catalogo_pacientes = Path(caminho_catalogo_pacientes)
        self.diretorio_saida = Path(diretorio_saida)
        self.integracao = integracao or IntegracaoPhysioNet()

    def _buscar_paciente(self, id_registro: str) -> dict[str, Any]:
        with self.caminho_catalogo_pacientes.open(encoding="utf-8") as arquivo_catalogo:
            pacientes = json.load(arquivo_catalogo)

        paciente = next(
            (
                paciente
                for paciente in pacientes.values()
                if paciente.get("id") == id_registro
            ),
            None,
        )
        if paciente is None:
            raise PacienteNaoLocalizadoError(id_registro)
        return paciente

    def baixar_dados_paciente(self, id_registro: str) -> dict[str, Any]:
        paciente = self._buscar_paciente(id_registro)
        caminho_csv = self.integracao.baixar_csv(paciente, self.diretorio_saida)
        GeradorGraficos().gerar(caminho_csv, paciente)
        caminho_relatorio = GeradorRelatorios(
            paciente,
            caminho_csv,
            caminho_csv.parent,
        ).gerar_relatorio()
        with caminho_relatorio.open(encoding="utf-8") as arquivo_relatorio:
            return json.load(arquivo_relatorio)
