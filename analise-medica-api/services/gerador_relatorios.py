import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


class GeradorRelatorios:
    CANAIS = {
        "HR": {
            "descricao": "Frequência cardíaca",
            "aliases": {"hr"},
            "unidade": "bpm",
            "fonte": "https://medlineplus.gov/ency/article/003399.htm",
        },
        "SpO2": {
            "descricao": "Saturação de oxigênio",
            "aliases": {"spo2"},
            "unidade": "%",
            "fonte": "https://medlineplus.gov/lab-tests/pulse-oximetry/",
        },
        "NBPs": {
            "descricao": "Pressão arterial sistólica",
            "aliases": {"nbps", "nbpsys"},
            "unidade": "mmHg",
            "fonte": "https://my.clevelandclinic.org/health/articles/10881-vital-signs",
        },
        "NBPd": {
            "descricao": "Pressão arterial diastólica",
            "aliases": {"nbpd", "nbpdias"},
            "unidade": "mmHg",
            "fonte": "https://my.clevelandclinic.org/health/articles/10881-vital-signs",
        },
        "PULSE": {
            "descricao": "Frequência de pulso periférico",
            "aliases": {"pulse"},
            "unidade": "bpm",
            "fonte": "https://medlineplus.gov/ency/article/003399.htm",
        },
        "RESP": {
            "descricao": "Frequência respiratória",
            "aliases": {"resp"},
            "unidade": "rpm",
            "fonte": "https://my.clevelandclinic.org/health/articles/10881-vital-signs",
        },
    }

    def __init__(
        self,
        paciente: dict[str, Any],
        caminho_csv: str | Path,
        diretorio_saida: str | Path | None = None,
    ) -> None:
        self.paciente = paciente
        self.caminho_csv = Path(caminho_csv)
        self.diretorio_saida = (
            Path(diretorio_saida)
            if diretorio_saida is not None
            else self.caminho_csv.parent
        )
        self.df = pd.read_csv(self.caminho_csv)
        self.colunas_normalizadas = {
            self._normalizar_nome(coluna): coluna for coluna in self.df.columns
        }

    @staticmethod
    def _normalizar_nome(nome: Any) -> str:
        return "".join(str(nome).casefold().split())

    def _encontrar_coluna(self, aliases: set[str]) -> str | None:
        for alias in aliases:
            if alias in self.colunas_normalizadas:
                return self.colunas_normalizadas[alias]
        return None

    def _obter_tempo_analisado(self) -> dict[str, Any]:
        coluna_tempo = self._encontrar_coluna({"tempo_segundos"})
        if coluna_tempo is None:
            return {
                "duracao_segundos": None,
                "duracao_formatada": None,
                "observacao": "O CSV não contém a coluna tempo_segundos.",
            }

        tempos = pd.to_numeric(self.df[coluna_tempo], errors="coerce")
        if tempos.notna().any():
            tempos = tempos.dropna()
        else:
            timestamps = pd.to_datetime(self.df[coluna_tempo], errors="coerce").dropna()
            if not timestamps.empty:
                tempos = (timestamps - timestamps.min()).dt.total_seconds()
            else:
                tempos = tempos.dropna()
        if tempos.empty:
            return {
                "duracao_segundos": None,
                "duracao_formatada": None,
                "observacao": "A coluna tempo_segundos não contém valores válidos.",
            }

        inicio = float(tempos.min())
        fim = float(tempos.max())
        intervalos = tempos.sort_values().diff()
        intervalos_validos = intervalos[intervalos > 0]
        if intervalos_validos.empty:
            return {
                "inicio_segundo": inicio,
                "fim_ultimo_sample_segundo": fim,
                "duracao_segundos": None,
                "duracao_formatada": None,
                "observacao": "Não foi possível inferir o intervalo de amostragem.",
            }

        intervalo_amostragem = float(intervalos_validos.median())
        duracao = fim - inicio + intervalo_amostragem
        minutos, segundos = divmod(round(duracao), 60)
        if minutos and segundos:
            formatada = f"{minutos} minuto(s) e {segundos} segundo(s)"
        elif minutos:
            formatada = f"{minutos} minuto(s)"
        else:
            formatada = f"{segundos} segundo(s)"

        return {
            "inicio_segundo": inicio,
            "fim_ultimo_sample_segundo": fim,
            "duracao_segundos": round(duracao, 2),
            "duracao_formatada": formatada,
            "intervalo_amostragem_segundos": round(intervalo_amostragem, 6),
            "observacao": (
                "Duração calculada pelo intervalo entre o primeiro e o último "
                "registro, acrescido de um intervalo de amostragem."
            ),
        }

    def _avaliar_canal(self, canal: str) -> dict[str, Any]:
        configuracao = self.CANAIS[canal]
        coluna = self._encontrar_coluna(configuracao["aliases"])
        resultado: dict[str, Any] = {
            "descricao": configuracao["descricao"],
            "coluna_csv": coluna,
            "unidade": configuracao["unidade"],
            "fonte": configuracao["fonte"],
        }

        if coluna is None:
            resultado["estatisticas"] = None
            return resultado

        valores = pd.to_numeric(self.df[coluna], errors="coerce")
        coluna_interpolada = f"{coluna}__interpolado"
        if coluna_interpolada in self.df.columns:
            estimados = (
                self.df[coluna_interpolada]
                .astype(str)
                .str.strip()
                .str.casefold()
                .isin({"true", "1", "yes", "sim"})
            )
            valores = valores[~estimados]
        valores = valores.dropna()
        if valores.empty:
            resultado["estatisticas"] = None
            return resultado

        resultado["estatisticas"] = {
            "quantidade": int(valores.count()),
            "minimo": round(float(valores.min()), 2),
            "maximo": round(float(valores.max()), 2),
            "media": round(float(valores.mean()), 2),
            "mediana": round(float(valores.median()), 2),
        }
        return resultado

    def avaliar_hr(self) -> dict[str, Any]:
        return self._avaliar_canal("HR")

    def avaliar_spo2(self) -> dict[str, Any]:
        return self._avaliar_canal("SpO2")

    def avaliar_nbps(self) -> dict[str, Any]:
        return self._avaliar_canal("NBPs")

    def avaliar_nbpd(self) -> dict[str, Any]:
        return self._avaliar_canal("NBPd")

    def avaliar_pulse(self) -> dict[str, Any]:
        return self._avaliar_canal("PULSE")

    def avaliar_resp(self) -> dict[str, Any]:
        return self._avaliar_canal("RESP")

    def montar_relatorio(self) -> dict[str, Any]:
        agora = datetime.now().astimezone()
        return {
            "dados_do_paciente": {
                "id": self.paciente.get("id"),
                "nome": self.paciente.get("nome"),
                "idade": self.paciente.get("idade"),
                "sexo": self.paciente.get("genero"),
                "data": agora.isoformat(timespec="seconds"),
            },
            "prontuario": self.paciente.get("prontuario")
            or "Não informado no cadastro.",
            "tempo_analisado": self._obter_tempo_analisado(),
            "sinais_vitais": {
                "HR": self.avaliar_hr(),
                "SpO2": self.avaliar_spo2(),
                "NBPs": self.avaliar_nbps(),
                "NBPd": self.avaliar_nbpd(),
                "PULSE": self.avaliar_pulse(),
                "RESP": self.avaliar_resp(),
            },
            "criterio_de_interpretacao": (
                "O relatório contém estatísticas dos valores numéricos disponíveis "
                "e uma análise informativa gerada por IA. Essa análise não é "
                "diagnóstico nem substitui avaliação profissional."
            ),
        }

    def salvar_relatorio(self, relatorio: dict[str, Any]) -> Path:
        agora = datetime.now().astimezone()
        nome_paciente = str(self.paciente["nome"]).upper().replace(" ", "_")
        nome_arquivo = (
            f"RELATORIO_{nome_paciente}_{agora.strftime('%d%m%Y_%H%M%S')}.json"
        )
        self.diretorio_saida.mkdir(parents=True, exist_ok=True)
        caminho_relatorio = self.diretorio_saida / nome_arquivo
        with caminho_relatorio.open("w", encoding="utf-8") as arquivo:
            json.dump(relatorio, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
            arquivo.write("\n")
        return caminho_relatorio

    def gerar_relatorio(self) -> Path:
        return self.salvar_relatorio(self.montar_relatorio())
