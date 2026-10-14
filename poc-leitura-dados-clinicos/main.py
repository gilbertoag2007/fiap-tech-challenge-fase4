
import downloader as dw
import matplotlib.pyplot as plt

# Registro documentado pelo PhysioNet https://physionet.org/content/mimic3wdb/1.0/31/3141595/
registro = "3141595n" # paciente
diretorio = "mimic3wdb/1.0/31/3141595"

df = dw.gerar_dataframe_dados_clinicos(diretorio=diretorio, registro=registro)

def gerar_graficos_sinais_vitais(df):
    # VISUALIZANDO OS DADOS EM GRÁFICOS
    # Selecionar canais disponíveis
    canais = [
        c for c in df.columns
        if c in ["HR", "SpO2", "NBPs", "NBPd", "NBPm"]
    ]
    #HR	Frequência cardíaca, geralmente calculada a partir do ECG	bpm
    #SpO2	Saturação periférica de oxigênio no sangue, medida por oxímetro de pulso	%
    #NBPs	Pressão arterial não invasiva sistólica	mmHg
    #NBPd	Pressão arterial não invasiva diastólica	mmHg
    #NBPm	Pressão arterial não invasiva média (PAM)	mmHg


    for canal in canais:
        plt.figure(figsize=(12, 3))

        plt.plot(
            df["tempo_segundos"],
            df[canal]
        )

        plt.title(f"Sinal vital: {canal}")
        plt.xlabel("Tempo (segundos)")
        plt.ylabel(canal)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f"grafico_{canal}.png", dpi=300)
        plt.close()


gerar_graficos_sinais_vitais(df)

