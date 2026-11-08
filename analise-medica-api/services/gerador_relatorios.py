import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


class GeradorRelatorios:
    CHAVE_REFERENCIA_POR_CANAL = {
        "HR": "frequencia_cardiaca",
        "SpO2": "saturacao_oxigenio",
        "NBPs": "pressao_arterial_sistolica",
        "NBPd": "pressao_arterial_diastolica",
        "PULSE": "frequencia_pulso_periferico",
        "RESP": "frequencia_respiratoria",
    }

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
        self.referencias_sinais_vitais = self._carregar_referencias_sinais_vitais()

    @staticmethod
    def _normalizar_nome(nome: Any) -> str:
        return "".join(str(nome).casefold().split())

    @staticmethod
    def _carregar_referencias_sinais_vitais() -> dict[str, Any]:
        caminho_arquivo = (
            Path(__file__).resolve().parents[1] / "data" / "referencias_sinais_vitais.json"
        )
        if not caminho_arquivo.exists():
            return {}

        with caminho_arquivo.open(encoding="utf-8") as arquivo:
            return json.load(arquivo)

    def _obter_referencia_canal(self, canal: str) -> dict[str, Any]:
        configuracao = self.CANAIS[canal]
        chave_sinal = self.CHAVE_REFERENCIA_POR_CANAL.get(canal)
        dados_referencia = {}

        if chave_sinal:
            dados_referencia = (
                self.referencias_sinais_vitais.get("sinais_vitais", {})
                .get(chave_sinal, {})
            )

        faixa_sexo = dados_referencia.get("sexo", {})
        faixa_adulta = dados_referencia.get("faixa_adulta_normal", {})
        faixa_por_idade = dados_referencia.get("faixa_por_idade", [])
        idade = self.paciente.get("idade")
        faixa_aplicada = dict(faixa_adulta)

        genero = str(self.paciente.get("genero", "")).strip().casefold()
        referencia_sexo = faixa_sexo.get(genero)
        if isinstance(referencia_sexo, str) and referencia_sexo:
            faixa_sexo_valores = {
                "minimo": None,
                "maximo": None,
            }
            partes = [
                part.strip()
                for part in referencia_sexo.replace("%", "").replace("mmhg", "").replace("bpm", "").replace("rpm", "").split("a")
            ]
            if len(partes) >= 2:
                try:
                    faixa_sexo_valores["minimo"] = float(partes[0].replace(",", "."))
                    faixa_sexo_valores["maximo"] = float(partes[1].replace(",", "."))
                except ValueError:
                    faixa_sexo_valores = {"minimo": None, "maximo": None}
            if faixa_sexo_valores["minimo"] is not None and faixa_sexo_valores["maximo"] is not None:
                faixa_aplicada = {**faixa_aplicada, **faixa_sexo_valores}

        if idade is not None:
            try:
                idade_numero = float(idade)
            except (TypeError, ValueError):
                idade_numero = None

            if idade_numero is not None and idade_numero < 18:
                faixa_selecionada = next(
                    (
                        faixa
                        for faixa in faixa_por_idade
                        if faixa.get("faixa_etaria")
                        and isinstance(faixa.get("minimo"), (int, float))
                        and isinstance(faixa.get("maximo"), (int, float))
                        and faixa.get("minimo") <= idade_numero <= faixa.get("maximo")
                    ),
                    None,
                )
                if faixa_selecionada:
                    faixa_aplicada = dict(faixa_selecionada)

        referencia_texto = faixa_aplicada.get(
            "observacao",
            configuracao["referencia"],
        )
        if faixa_aplicada.get("minimo") is not None and faixa_aplicada.get("maximo") is not None:
            referencia_texto = (
                f"{faixa_aplicada['minimo']} a {faixa_aplicada['maximo']} "
                f"{configuracao['unidade']}"
            )

        return {
            "minimo": faixa_aplicada.get("minimo", configuracao["minimo"]),
            "maximo": faixa_aplicada.get("maximo", configuracao["maximo"]),
            "limite_superior_exclusivo": configuracao.get(
                "limite_superior_exclusivo",
                False,
            ),
            "referencia": referencia_texto,
            "fonte": configuracao["fonte"],
        }

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
        referencia = self._obter_referencia_canal(canal)
        coluna = self._encontrar_coluna(configuracao["aliases"])
        resultado: dict[str, Any] = {
            "descricao": configuracao["descricao"],
            "coluna_csv": coluna,
            "unidade": configuracao["unidade"],
            "fonte": referencia["fonte"],
        }

        if coluna is None:
            resultado.update(
                status="Não disponível",
                estatisticas=None,
                observacao="O canal não está presente no CSV.",
            )
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

        if idade is None or pd.isna(idade):
            resultado.update(
                status="Não avaliado",
                observacao=(
                    "Não foi possível aplicar as faixas de referência porque a idade "
                    "do paciente não foi informada."
                ),
            )
            return resultado

        minimo = referencia["minimo"]
        maximo = referencia["maximo"]
        if minimo is None or maximo is None:
            resultado.update(
                status="Não avaliado",
                observacao=(
                    "As referências do arquivo de configuração não possuem faixa de "
                    "aplicação válida para esse sinal."
                ),
            )
            return resultado

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
                f"ficaram fora da faixa de referência informada ({minimo} a {maximo} {configuracao['unidade']}). "
                "Isso é uma sinalização automatizada, não um diagnóstico."
            )
        else:
            status = "Normal"
            observacao = (
                "Todos os valores disponíveis ficaram dentro da faixa de "
                f"referência informada ({minimo} a {maximo} {configuracao['unidade']}); "
                "isso não substitui avaliação clínica."
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
