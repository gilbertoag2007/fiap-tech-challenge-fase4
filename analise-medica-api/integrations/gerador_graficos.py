from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


class GeradorGraficos:
    ALIASES_CANAIS = {
        "HR": {"hr"},
        "SpO2": {"spo2"},
        "NBPs": {"nbps", "nbpsys"},
        "NBPd": {"nbpd", "nbpdias"},
        "PULSE": {"pulse"},
        "RESP": {"resp"},
    }

    def gerar(
        self,
        caminho_csv: str | Path,
        paciente: dict[str, Any],
    ) -> list[Path]:
        caminho_csv = Path(caminho_csv)
        diretorio_saida = caminho_csv.parent
        dataframe = pd.read_csv(caminho_csv)
        colunas_normalizadas = {
            "".join(str(coluna).casefold().split()): coluna
            for coluna in dataframe.columns
        }
        canais = [
            (nome_canal, coluna)
            for nome_canal, aliases in self.ALIASES_CANAIS.items()
            if (
                coluna := next(
                    (
                        colunas_normalizadas[alias]
                        for alias in aliases
                        if alias in colunas_normalizadas
                    ),
                    None,
                )
            )
            is not None
        ]

        arquivos_gerados = []
        nome_paciente = "_".join(str(paciente["nome"]).upper().split())
        data_hora = diretorio_saida.name

        for nome_canal, coluna in canais:
            if not dataframe[coluna].notna().any():
                continue

            figura, eixo = plt.subplots(figsize=(12, 3))
            try:
                eixo.plot(dataframe["tempo_segundos"], dataframe[coluna])
                eixo.set_title(f"Sinal vital: {nome_canal}")
                eixo.set_xlabel("Tempo (segundos)")
                eixo.set_ylabel(nome_canal)
                eixo.grid(True)
                figura.tight_layout()

                nome_arquivo = (
                    f"grafico_{nome_canal}_{paciente['id']}_"
                    f"{nome_paciente}_{data_hora}.png"
                )
                caminho_grafico = diretorio_saida / nome_arquivo
                figura.savefig(caminho_grafico, dpi=300)
                arquivos_gerados.append(caminho_grafico)
            finally:
                plt.close(figura)

        return arquivos_gerados
