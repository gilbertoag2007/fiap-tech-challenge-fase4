import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from integrations.gerador_graficos import GeradorGraficos
from integrations.integracao_physionet import IntegracaoPhysioNet
from services.gerador_relatorios import GeradorRelatorios


class PacienteNaoLocalizadoError(Exception):
    pass


class RelatorioNaoLocalizadoError(Exception):
    pass


class GraficosNaoLocalizadosError(Exception):
    pass


class SinaisVitaisDetalhadosNaoLocalizadosError(Exception):
    pass


class ServicoSinaisVitais:
    CHAVE_REFERENCIA_POR_CANAL = {
        "HR": "frequencia_cardiaca",
        "SpO2": "saturacao_oxigenio",
        "NBPs": "pressao_arterial_sistolica",
        "NBPd": "pressao_arterial_diastolica",
        "PULSE": "frequencia_pulso_periferico",
        "RESP": "frequencia_respiratoria",
    }

    def __init__(
        self,
        caminho_catalogo_pacientes: str | Path,
        diretorio_saida: str | Path,
        integracao: IntegracaoPhysioNet | None = None,
    ) -> None:
        self.caminho_catalogo_pacientes = Path(caminho_catalogo_pacientes)
        self.diretorio_saida = Path(diretorio_saida)
        self.integracao = integracao or IntegracaoPhysioNet()

    def _carregar_referencias_sinais_vitais(self) -> dict[str, Any]:
        caminho_arquivo = self.diretorio_saida / "referencias_sinais_vitais.json"
        if not caminho_arquivo.exists():
            return {"sinais_vitais": {}}

        with caminho_arquivo.open(encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        return dados if isinstance(dados, dict) else {"sinais_vitais": {}}

    def listar_tabelas_referencia(self) -> dict[str, Any]:
        dados = self._carregar_referencias_sinais_vitais()
        referencias = dados.get("sinais_vitais", {})
        tabelas = {}

        for codigo, chave in self.CHAVE_REFERENCIA_POR_CANAL.items():
            if chave in referencias:
                tabelas[codigo] = referencias[chave]

        return tabelas

    def recuperar_tabela_referencia(self, sinal: str) -> dict[str, Any]:
        chave_sinal = (sinal or "").strip()
        if not chave_sinal:
            raise ValueError("Sinal vital não informado.")

        sinal_normalizado = "".join(ch for ch in chave_sinal.upper() if ch.isalnum())
        referencias = self.listar_tabelas_referencia()
        codigo_por_alias = {
            "HR": "HR",
            "SPO2": "SpO2",
            "NBPS": "NBPs",
            "NBPD": "NBPd",
            "PULSE": "PULSE",
            "RESP": "RESP",
            "FREQUENCIACARDIACA": "HR",
            "SATURACAOOXIGENIO": "SpO2",
            "PRESSAOARTERIALSISTOLICA": "NBPs",
            "PRESSAOARTERIALDIASTOLICA": "NBPd",
            "FREQUENCIAPULSOPERIFERICO": "PULSE",
            "FREQUENCIARESPIRATORIA": "RESP",
        }

        codigo = codigo_por_alias.get(sinal_normalizado)
        if codigo and codigo in referencias:
            return referencias[codigo]

        raise ValueError(f"Tabela de referência não localizada para o sinal '{sinal}'.")

    def listar_pacientes(self) -> list[dict[str, Any]]:
        with self.caminho_catalogo_pacientes.open(encoding="utf-8") as arquivo_catalogo:
            pacientes = json.load(arquivo_catalogo)

        campos_publicos = ("id", "cpf", "nome", "idade", "genero", "prontuario")
        return [
            {campo: paciente[campo] for campo in campos_publicos}
            for paciente in pacientes.values()
        ]

    def _buscar_paciente_por_identificadores(
        self,
        cpf: str | None,
        id_registro: str | None,
    ) -> dict[str, Any] | None:
        with self.caminho_catalogo_pacientes.open(encoding="utf-8") as arquivo_catalogo:
            pacientes = json.load(arquivo_catalogo)

        return next(
            (
                paciente
                for paciente in pacientes.values()
                if (cpf is None or paciente.get("cpf") == cpf)
                and (id_registro is None or paciente.get("id") == id_registro)
            ),
            None,
        )

    @staticmethod
    def _arquivos_mais_recentes(
        diretorio_paciente: Path,
        padrao: str,
    ) -> list[Path]:
        execucoes_com_arquivos = []
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

                arquivos = sorted(diretorio_execucao.glob(padrao))
                if arquivos:
                    execucoes_com_arquivos.append((data_hora_execucao, arquivos))

        if not execucoes_com_arquivos:
            return []

        _, arquivos_mais_recentes = max(
            execucoes_com_arquivos,
            key=lambda execucao: execucao[0],
        )
        return arquivos_mais_recentes

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
        paciente = self._buscar_paciente_por_identificadores(cpf, id_registro)
        if paciente is None:
            raise RelatorioNaoLocalizadoError

        nome_paciente = "_".join(str(paciente["nome"]).upper().split())
        diretorio_paciente = self.diretorio_saida / nome_paciente
        relatorios = self._arquivos_mais_recentes(
            diretorio_paciente,
            "RELATORIO_*.json",
        )
        if not relatorios:
            raise RelatorioNaoLocalizadoError

        with relatorios[-1].open(encoding="utf-8") as arquivo_relatorio:
            return json.load(arquivo_relatorio)

    def recuperar_graficos_zip(
        self,
        cpf: str | None = None,
        id_registro: str | None = None,
    ) -> tuple[bytes, str]:
        paciente = self._buscar_paciente_por_identificadores(cpf, id_registro)
        if paciente is None:
            raise GraficosNaoLocalizadosError

        nome_paciente = "_".join(str(paciente["nome"]).upper().split())
        diretorio_paciente = self.diretorio_saida / nome_paciente
        graficos = self._arquivos_mais_recentes(diretorio_paciente, "*.png")
        if not graficos:
            raise GraficosNaoLocalizadosError

        conteudo_zip = BytesIO()
        with ZipFile(conteudo_zip, mode="w", compression=ZIP_DEFLATED) as arquivo_zip:
            for grafico in graficos:
                arquivo_zip.write(grafico, arcname=grafico.name)

        data_hora_execucao = graficos[0].parent.name
        nome_arquivo = f"GRAFICOS_{nome_paciente}_{data_hora_execucao}.zip"
        return conteudo_zip.getvalue(), nome_arquivo

    def recuperar_csv(self, cpf: str, id_registro: str) -> Path:
        paciente = self._buscar_paciente_por_identificadores(cpf, id_registro)
        if paciente is None:
            raise SinaisVitaisDetalhadosNaoLocalizadosError

        nome_paciente = "_".join(str(paciente["nome"]).upper().split())
        diretorio_paciente = self.diretorio_saida / nome_paciente
        arquivos_csv = self._arquivos_mais_recentes(
            diretorio_paciente,
            f"SINAIS_VITAIS_{paciente['id']}_*.csv",
        )
        if not arquivos_csv:
            raise SinaisVitaisDetalhadosNaoLocalizadosError
        return arquivos_csv[-1]

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
