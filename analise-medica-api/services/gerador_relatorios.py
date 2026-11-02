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
            "minimo": 60,
            "maximo": 100,
            "referencia": "60 a 100 bpm em adultos em repouso.",
            "fonte": "https://medlineplus.gov/ency/article/003399.htm",
        },
        "SpO2": {
            "descricao": "Saturação de oxigênio",
            "aliases": {"spo2"},
            "unidade": "%",
            "minimo": 95,
            "maximo": 100,
            "referencia": "95% a 100% como faixa usual; pode variar em doenças pulmonares ou altitude elevada.",
            "fonte": "https://medlineplus.gov/lab-tests/pulse-oximetry/",
        },
        "NBPs": {
            "descricao": "Pressão arterial sistólica",
            "aliases": {"nbps", "nbpsys"},
            "unidade": "mmHg",
            "minimo": 90,
            "maximo": 120,
            "limite_superior_exclusivo": True,
            "referencia": "90 a menos de 120 mmHg; a classificação da pressão arterial deve considerar também a medida diastólica.",
            "fonte": "https://my.clevelandclinic.org/health/articles/10881-vital-signs",
        },
        "NBPd": {
            "descricao": "Pressão arterial diastólica",
            "aliases": {"nbpd", "nbpdias"},
            "unidade": "mmHg",
            "minimo": 60,
            "maximo": 80,
            "limite_superior_exclusivo": True,
            "referencia": "60 a menos de 80 mmHg; a classificação da pressão arterial deve considerar também a medida sistólica.",
            "fonte": "https://my.clevelandclinic.org/health/articles/10881-vital-signs",
        },
        "PULSE": {
            "descricao": "Frequência de pulso periférico",
            "aliases": {"pulse"},
            "unidade": "bpm",
            "minimo": 60,
            "maximo": 100,
            "referencia": "60 a 100 bpm em adultos em repouso.",
            "fonte": "https://medlineplus.gov/ency/article/003399.htm",
        },
        "RESP": {
            "descricao": "Frequência respiratória",
            "aliases": {"resp"},
            "unidade": "rpm",
            "minimo": 12,
            "maximo": 18,
            "referencia": "12 a 18 respirações por minuto em adultos.",
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

        tempos = pd.to_numeric(self.df[coluna_tempo], errors="coerce").dropna()
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
            "referencia_adulto": configuracao["referencia"],
            "fonte": configuracao["fonte"],
        }

        if coluna is None:
            resultado.update(
                status="Não disponível",
                estatisticas=None,
                observacao="O canal não está presente no CSV.",
            )
            return resultado

        valores = pd.to_numeric(self.df[coluna], errors="coerce").dropna()
        if valores.empty:
            resultado.update(
                status="Não disponível",
                estatisticas=None,
                observacao="O canal está no CSV, mas não possui valores numéricos disponíveis.",
            )
            return resultado

        resultado["estatisticas"] = {
            "quantidade": int(valores.count()),
            "minimo": round(float(valores.min()), 2),
            "maximo": round(float(valores.max()), 2),
            "media": round(float(valores.mean()), 2),
            "mediana": round(float(valores.median()), 2),
        }

        try:
            idade = float(self.paciente["idade"])
        except (KeyError, TypeError, ValueError):
            idade = None

        if idade is None or pd.isna(idade) or idade < 18:
            resultado.update(
                status="Não avaliado",
                observacao=(
                    "As referências configuradas são para adultos; "
                    "não foi aplicada uma faixa pediátrica."
                ),
            )
            return resultado

        minimo = configuracao["minimo"]
        maximo = configuracao["maximo"]
        fora_da_faixa = (valores < minimo) | (valores > maximo)
        if configuracao.get("limite_superior_exclusivo"):
            fora_da_faixa = (valores < minimo) | (valores >= maximo)

        quantidade_fora = int(fora_da_faixa.sum())
        total = int(valores.count())
        if quantidade_fora:
            percentual_fora = quantidade_fora / total * 100
            status = "Alterada"
            observacao = (
                f"{quantidade_fora} de {total} valores ({percentual_fora:.1f}%) "
                "ficaram fora da faixa de referência informada. "
                "Isso é uma sinalização automatizada, não um diagnóstico."
            )
        else:
            status = "Normal"
            observacao = (
                "Todos os valores disponíveis ficaram dentro da faixa de "
                "referência informada; isso não substitui avaliação clínica."
            )

        resultado.update(status=status, observacao=observacao)
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

    def gerar_relatorio(self) -> Path:
        agora = datetime.now().astimezone()
        nome_paciente = str(self.paciente["nome"]).upper().replace(" ", "_")
        nome_arquivo = (
            f"RELATORIO_{nome_paciente}_{agora.strftime('%d%m%Y_%H%M%S')}.json"
        )

        relatorio = {
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
                "Foram comparados os valores numéricos disponíveis com faixas "
                "gerais para adultos. A classificação considera Alterada se ao "
                "menos uma amostra estiver fora da faixa; sexo, repouso, "
                "condições clínicas, altitude e contexto de medição não foram "
                "usados para personalizar os limites. O resultado não é diagnóstico."
            ),
        }

        self.diretorio_saida.mkdir(parents=True, exist_ok=True)
        caminho_relatorio = self.diretorio_saida / nome_arquivo
        with caminho_relatorio.open("w", encoding="utf-8") as arquivo:
            json.dump(relatorio, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
            arquivo.write("\n")
        return caminho_relatorio
