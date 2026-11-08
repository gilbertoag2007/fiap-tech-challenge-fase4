import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import wfdb
from wfdb.io._url import NetFileError


class ErroRegistroExterno(Exception):
    pass


def interpolar_lacunas(dataframe: pd.DataFrame) -> pd.DataFrame:
    for coluna in dataframe.columns:
        if coluna == "tempo_segundos":
            continue

        valores = pd.to_numeric(dataframe[coluna], errors="coerce")
        ausentes = valores.isna()
        if not ausentes.any() or not valores.notna().any():
            continue

        valores_interpolados = valores.interpolate(
            method="linear",
            limit_direction="both",
        )
        dataframe[coluna] = valores_interpolados
        dataframe[f"{coluna}__interpolado"] = (
            ausentes & valores_interpolados.notna()
        )

    return dataframe


class IntegracaoPhysioNet:
    def baixar_csv(
        self,
        paciente: dict[str, Any],
        diretorio_saida: str | Path,
    ) -> Path:
        try:
            record = wfdb.rdrecord(
                paciente["id"],
                pn_dir=paciente["diretorio"],
                sampfrom=0,
                sampto=600,
            )
        except NetFileError as error:
            raise ErroRegistroExterno(str(error)) from error

        dataframe = pd.DataFrame(record.p_signal, columns=record.sig_name)
        data_inicial = datetime(2026, 1, 1)
        data_final = datetime(2026, 11, 8)
        data_hora_inicio = (
            data_inicial
            + timedelta(days=random.randint(0, (data_final - data_inicial).days))
            + timedelta(seconds=random.randint(6 * 60 * 60, 18 * 60 * 60))
        )
        dataframe.insert(
            0,
            "tempo_segundos",
            [
                (data_hora_inicio + timedelta(seconds=index / record.fs)).strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )
                for index in range(len(dataframe))
            ],
        )
        interpolar_lacunas(dataframe)

        nome_paciente = "_".join(paciente["nome"].upper().split())
        data_hora_diretorio = datetime.now().strftime("%Y%m%d_%H%M%S")
        diretorio_paciente = Path(diretorio_saida) / nome_paciente
        diretorio_execucao = diretorio_paciente / data_hora_diretorio
        diretorio_execucao.mkdir(parents=True, exist_ok=True)

        data_hora_arquivo = datetime.now().strftime("%Y%m%d_%H%M")
        nome_arquivo = (
            f"SINAIS_VITAIS_{paciente['id']}_{nome_paciente}_{data_hora_arquivo}.csv"
        )
        caminho_csv = diretorio_execucao / nome_arquivo
        dataframe.to_csv(caminho_csv, index=False)
        return caminho_csv
