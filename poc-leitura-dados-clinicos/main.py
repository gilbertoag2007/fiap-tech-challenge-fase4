
from pathlib import Path

import downloader as dw
import matplotlib.pyplot as plt
from gerador_relatorios import GeradorRelatorios

paciente_1 = {
"id": "3000190n",
"nome": "Carlos Alberto Lima",
"idade": 55,
"genero": "Masculino",
"prontuario": "paciente com histórico de hipertensão e diabetes. Faz uso diário de Glifage e ARA II",
"diretorio": "mimic3wdb/1.0/30/3000190",
"link": "https://physionet.org/files/mimic3wdb/1.0/30/3000190/3000190n.hea"
}

paciente_2 = {
"id": "3000086n",
"nome": "Leticia Freitas",
"idade": 18,
"genero": "Feminino",
"prontuario": "paciente com histórico de asma. Faz uso diário de Salbutamol",
"diretorio": "mimic3wdb/1.0/30/3000086",
"link": "https://physionet.org/files/mimic3wdb/1.0/30/3000086/3000086n.hea"
}

paciente_3 = {
"id": "3141595n",
"nome": "Juliana Oliveira",
"idade": 45,
"genero": "Feminino",
"prontuario": "paciente com histórico de hipertensão. Faz uso diário de Captopril",
"diretorio": "mimic3wdb/1.0/31/3141595",
"link": "https://physionet.org/files/mimic3wdb/1.0/31/3141595/3141595n.hea"
}

#df = dw.gerar_dataframe_dados_clinicos(diretorio=diretorio, registro=registro)
diretorio_saida = dw.gerar_diretorio_saida(paciente_3)
df = dw.gerar_dataframe_dados_clinicos(paciente_3, diretorio_saida)

print(colunas := df.columns)


def gerar_graficos_sinais_vitais(df, paciente, diretorio_saida):
    aliases_canais = {
        "HR": {"hr"},
        "SpO2": {"spo2"},
        "NBPs": {"nbps", "nbpsys"},
        "NBPd": {"nbpd", "nbpdias"},
        "PULSE": {"pulse"},
        "RESP": {"resp"},
    }
    colunas_normalizadas = {
        "".join(str(coluna).casefold().split()): coluna
        for coluna in df.columns
    }
    canais = [
        (nome_canal, coluna)
        for nome_canal, aliases in aliases_canais.items()
        if (coluna := next(
            (
                colunas_normalizadas[alias]
                for alias in aliases
                if alias in colunas_normalizadas
            ),
            None,
        )) is not None
    ]

    for nome_canal, canal in canais:
        if not df[canal].notna().any():
            continue

        plt.figure(figsize=(12, 3))

        plt.plot(
            df["tempo_segundos"],
            df[canal]
        )

        plt.title(f"Sinal vital: {nome_canal}")
        plt.xlabel("Tempo (segundos)")
        plt.ylabel(nome_canal)
        plt.grid(True)
        plt.tight_layout()
        nome_paciente = paciente["nome"].upper().replace(" ", "_")
        data_hora = Path(diretorio_saida).name
        nome_arquivo = (
            f"grafico_{nome_canal}_{paciente['id']}_{nome_paciente}_{data_hora}.png"
        )
        plt.savefig(Path(diretorio_saida) / nome_arquivo, dpi=300)
        plt.close()


gerar_graficos_sinais_vitais(df, paciente_3, diretorio_saida)

caminho_csv = next(Path(diretorio_saida).glob("*.csv"))
gerador_relatorios = GeradorRelatorios(
    paciente_3,
    caminho_csv,
    diretorio_saida,
)
caminho_relatorio = gerador_relatorios.gerar_relatorio()
print(f"Relatório JSON gerado: {caminho_relatorio}")
