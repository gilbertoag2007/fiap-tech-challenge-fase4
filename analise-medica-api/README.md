# analise-medica-api

API FastAPI para baixar sinais vitais dos registros cadastrados em
`data/pacientes.json`.

## Executar localmente

No PowerShell, a partir da raiz do repositório:

```powershell
cd analise-medica-api
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Alternativamente, a partir da raiz, execute:

```powershell
uvicorn main:app --app-dir analise-medica-api --reload
```

O objeto FastAPI está definido em `main.py`. As rotas automáticas de
documentação e OpenAPI estão disponíveis em `/docs` e `/openapi.json`.

Arquivos gerados durante a execução (relatórios `.json`, dados `.csv` e
gráficos `.png`) devem ser armazenados em `data/`. Os arquivos gerados são
ignorados pelo Git; `data/pacientes.json` e o marcador da pasta são versionados.

## Camadas

- `controller/`: valida a requisição HTTP e mapeia erros para respostas HTTP.
- `services/`: localiza pacientes no catálogo e coordena a operação.
- `integrations/`: consulta o PhysioNet, transforma o registro em CSV e gera
  gráficos PNG dos canais disponíveis.

## Baixar sinais vitais

Envie uma requisição `POST` para `/v1/sinais-vitais/` com o ID cadastrado:

```json
{
  "id": "3000190n"
}
```

O CSV, o relatório JSON de anomalias e os gráficos PNG são salvos em
`data/<NOME_DO_PACIENTE>/<YYYYMMDD_HHMMSS>/`. O relatório é calculado a partir
do CSV, seguindo as mesmas faixas e regras do gerador de relatórios do projeto.
Os gráficos são gerados para HR, SpO2, NBPs, NBPd, PULSE e RESP quando a coluna
existe e possui valores.
Se o registro não estiver em `data/pacientes.json`, a API responde com HTTP 404
e a mensagem `Paciente não localizado`. Falhas ao consultar o PhysioNet
retornam HTTP 502.
