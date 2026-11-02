from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import wfdb
from wfdb.io._url import NetFileError


class ErroRegistroExterno(Exception):
    pass


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
        dataframe.insert(
            0,
            "tempo_segundos",
            [index / record.fs for index in range(len(dataframe))],
        )

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
