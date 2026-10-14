import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://physionet.org/files/mimic3wdb/1.0"

resposta = requests.get(
    f"{BASE}/RECORDS-numerics",
    timeout=60
)
resposta.raise_for_status()

registros = [
    linha.strip()
    for linha in resposta.text.splitlines()
    if linha.strip()
]

# Excluir o registro já utilizado
registros = [
    r for r in registros
    if not r.endswith("/3141595n")
]

def verificar_registro(caminho):
    try:
        url = f"{BASE}/{caminho}.hea"
        r = requests.get(url, timeout=15)
        r.raise_for_status()

        linhas = r.text.splitlines()[1:]

        canais = set()

        for linha in linhas:
            partes = linha.split()
            if len(partes) >= 9:
                canais.add(
                    " ".join(partes[8:]).strip().lower()
                )

        obrigatorios = {
            "hr",
            "spo2",
            "nbp sys",
            "nbp dias",
            "nbp mean"
        }

        if obrigatorios.issubset(canais):
            return caminho, url, sorted(canais)

    except requests.RequestException:
        pass

    return None


encontrados = []

with ThreadPoolExecutor(max_workers=8) as executor:
    tarefas = [
        executor.submit(verificar_registro, r)
        for r in registros[:500]
    ]

    for tarefa in as_completed(tarefas):
        resultado = tarefa.result()

        if resultado:
            encontrados.append(resultado)

for caminho, url, canais in encontrados[:4]:
    print(f"\nRegistro: {caminho.split('/')[-1]}")
    print(f"Cabeçalho: {url}")
    print(f"Canais: {canais}")