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

### Listar pacientes

Envie uma requisição `GET` para `/v1/sinais-vitais/paciente`, sem body. A
resposta contém os campos `id`, `cpf`, `nome`, `idade`, `genero` e `prontuario`
de cada paciente cadastrado em `data/pacientes.json`.

### Recuperar relatório de análise

Envie uma requisição `GET` para `/v1/sinais-vitais/relatorio` com `cpf`, `id`
ou ambos como query params. Quando ambos forem informados, eles devem
corresponder ao mesmo paciente. A API retorna o conteúdo do relatório JSON mais
recente disponível para esse paciente ou HTTP 404 com `Relatório não localizado.`
quando não houver correspondência ou relatório.

### Baixar gráficos

Envie uma requisição `GET` para `/v1/sinais-vitais/graficos` com `cpf`, `id`
ou ambos como query params. Quando ambos forem informados, eles devem
corresponder ao mesmo paciente. A API retorna um arquivo ZIP com os gráficos
PNG da execução mais recente que possui imagens. Se não houver gráficos para o
paciente, responde com HTTP 404 e `Gráficos não localizados para o paciente informado.`

### Recuperar CSV detalhado dos sinais vitais

Envie uma requisição `GET` para `/v1/sinais-vitais/datalhamento` com `cpf`,
`id` ou ambos como query params:

```text
/v1/sinais-vitais/datalhamento?cpf=12345678900&id=3000190n
```

Quando ambos forem informados, eles devem corresponder ao mesmo paciente. A API
retorna como anexo o CSV da execução mais recente disponível na pasta desse
paciente. Se nenhum parâmetro for informado, responde com HTTP 422. Se o
paciente não corresponder aos identificadores ou o CSV não for localizado,
responde com HTTP 404 e
`Arquivo detalhado com os sinais vitais do paciente selecionado não foi localizado.`

### Baixar sinais vitais de um paciente

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
