import json
from datetime import datetime
from pathlib import Path
from typing import Any

from integrations.gerador_graficos import GeradorGraficos
from integrations.integracao_physionet import IntegracaoPhysioNet
from services.gerador_relatorios import GeradorRelatorios


class PacienteNaoLocalizadoError(Exception):
    pass


class RelatorioNaoLocalizadoError(Exception):
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

    def listar_pacientes(self) -> list[dict[str, Any]]:
        with self.caminho_catalogo_pacientes.open(encoding="utf-8") as arquivo_catalogo:
            pacientes = json.load(arquivo_catalogo)

        campos_publicos = ("id", "cpf", "nome", "idade", "genero", "prontuario")
        return [
            {campo: paciente[campo] for campo in campos_publicos}
            for paciente in pacientes.values()
        ]

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

    def recuperar_relatorio(
        self,
        cpf: str | None = None,
        id_registro: str | None = None,
    ) -> dict[str, Any]:
        with self.caminho_catalogo_pacientes.open(encoding="utf-8") as arquivo_catalogo:
            pacientes = json.load(arquivo_catalogo)

        paciente = next(
            (
                paciente
                for paciente in pacientes.values()
                if (cpf is None or paciente.get("cpf") == cpf)
                and (id_registro is None or paciente.get("id") == id_registro)
            ),
            None,
        )
        if paciente is None:
            raise RelatorioNaoLocalizadoError

        nome_paciente = "_".join(str(paciente["nome"]).upper().split())
        diretorio_paciente = self.diretorio_saida / nome_paciente
        execucoes_com_relatorio = []
        if diretorio_paciente.is_dir():
            for diretorio_execucao in diretorio_paciente.iterdir():
                if not diretorio_execucao.is_dir():
                    continue
                try:
                    data_hora_execucao = datetime.strptime(
                        diretorio_execucao.name,
                        "%Y%m%d_%H%M%S",
                    )
                except ValueError:
                    continue

                relatorios = sorted(diretorio_execucao.glob("RELATORIO_*.json"))
                if relatorios:
                    execucoes_com_relatorio.append((data_hora_execucao, relatorios))

        if not execucoes_com_relatorio:
            raise RelatorioNaoLocalizadoError

        _, relatorios_mais_recentes = max(
            execucoes_com_relatorio,
            key=lambda execucao: execucao[0],
        )
        with relatorios_mais_recentes[-1].open(encoding="utf-8") as arquivo_relatorio:
            return json.load(arquivo_relatorio)

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
