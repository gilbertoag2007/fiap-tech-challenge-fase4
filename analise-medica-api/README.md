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

Arquivos gerados durante a execução (relatórios `.json` e dados `.csv`) devem
ser armazenados em `data/`. Os arquivos gerados são ignorados pelo Git;
`data/pacientes.json` e o marcador da pasta são versionados.

## Camadas

- `controller/`: valida a requisição HTTP e mapeia erros para respostas HTTP.
- `services/`: localiza pacientes no catálogo e coordena a operação.
- `integrations/`: consulta o PhysioNet e transforma o registro em CSV.

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

### Configurar a análise com OpenAI

Copie `.env.example` para `.env` na pasta `analise-medica-api` e informe sua
chave em `OPENAI_API_KEY`. `OPENAI_MODEL` define o modelo (o padrão é
`gpt-6-luna`) e `OPENAI_BASE_URL` define o endpoint da API. O arquivo `.env` é
ignorado pelo Git; não versione sua chave. Instale as dependências atualizadas
com `pip install -r requirements.txt`.

Durante uma importação, a integração envia à OpenAI idade, sexo, histórico
médico do cadastro e estatísticas resumidas dos sinais. Nome, CPF, identificador
do paciente e CSV bruto não são enviados. O uso de dados clínicos em serviço
externo deve estar autorizado e de acordo com os requisitos de privacidade da
organização. A resposta é informativa, não substitui avaliação profissional.
Sem chave configurada, a rota de importação responde HTTP 503; falhas da API ou
uma resposta estruturada inválida respondem HTTP 502.

Envie uma requisição `POST` para `/v1/sinais-vitais/` com o ID cadastrado:

```json
{
  "id": "3000190n"
}
```

O CSV e o relatório JSON descritivo são salvos em
`data/<NOME_DO_PACIENTE>/<YYYYMMDD_HHMMSS>/`. O relatório é calculado a partir
do CSV, contém estatísticas descritivas dos sinais vitais e incorpora `status`
e `analise_ia` de cada sinal. Uma lista com os campos `sinal_vital`, `status` e
`analise_ia` também é salva em `ANALISE_IA_SINAIS_VITAIS.json` na pasta da
execução.
Todas as lacunas dos sinais numéricos são preenchidas por interpolação linear;
lacunas nas extremidades recebem o valor observado mais próximo. Sinais sem
nenhuma medição permanecem vazios por não haver referência para estimativa.
Cada sinal interpolado tem uma coluna `<nome_do_sinal>__interpolado` com
`True` nos valores estimados. Esses valores são exibidos nos gráficos como
estimativas e não são considerados nas estatísticas ou classificações do
relatório.
Se o registro não estiver em `data/pacientes.json`, a API responde com HTTP 404
e a mensagem `Paciente não localizado`. Falhas ao consultar o PhysioNet
retornam HTTP 502.
