from email import header

import wfdb
import pandas as pd


def gerar_dataframe_dados_clinicos(registro, diretorio):



    # Primeiro, consultar apenas o cabeçalho
    header = wfdb.rdheader(registro,pn_dir=diretorio)

    print("Frequência:", header.fs)
    print("Sinais disponíveis:", header.sig_name)

    # Ler apenas os primeiros 600 segundos
    dados = wfdb.rdrecord(
        registro,
        pn_dir=diretorio,
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
    df.to_csv(
        "sinais_vitais_mimic3.csv",
        index=False
    )

    print("Arquivo CSV gerado com sucesso!")

    return df