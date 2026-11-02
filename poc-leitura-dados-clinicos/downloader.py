from email import header
from datetime import datetime
from pathlib import Path

import wfdb
import pandas as pd


def gerar_nome_arquivo_sinais_vitais(paciente):
    nome = paciente["nome"].upper().replace(" ", "_")
    data_hora = datetime.now().strftime("%Y%m%d_%H%M")
    return f"SINAIS_VITAIS_{paciente['id']}_{nome}_{data_hora}"


def gerar_diretorio_saida(paciente):
    nome_paciente = paciente["nome"].upper().replace(" ", "_")
    data_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    diretorio_dados = Path(__file__).resolve().parent / "data"
    return diretorio_dados / nome_paciente / data_hora


def gerar_dataframe_dados_clinicos(paciente, diretorio_saida=None):



    # Primeiro, consultar apenas o cabeçalho
    header = wfdb.rdheader(paciente["id"],pn_dir=paciente["diretorio"])

    print("Frequência:", header.fs)
    print("Sinais disponíveis:", header.sig_name)

    # Ler apenas os primeiros 600 segundos
    dados = wfdb.rdrecord(
        paciente["id"],
        pn_dir=paciente["diretorio"],
        sampfrom=0,
        sampto=600 #600 segundos de dados
    )

    # Converter para DataFrame
    df = pd.DataFrame(
        dados.p_signal,
        columns=dados.sig_name
    )

    df.insert(
        0,
        "tempo_segundos",
        [i / dados.fs for i in range(len(df))]
    )

    print(df.head())

    # Salvar localmente em CSV
    if diretorio_saida is None:
        diretorio_saida = gerar_diretorio_saida(paciente)
    diretorio_saida = Path(diretorio_saida)
    diretorio_saida.mkdir(parents=True, exist_ok=True)
    nome_arquivo = gerar_nome_arquivo_sinais_vitais(paciente)
    df.to_csv(diretorio_saida / f"{nome_arquivo}.csv", index=False)

    print("Arquivo CSV gerado com sucesso!")

    return df