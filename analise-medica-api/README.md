# analise-medica-api

## Módulo de fisioterapia (Fase 4)

A API também oferece análise de quatro exercícios do REHAB24-6 em `/v1/fisioterapia`, com YOLOv8 Pose, classificação por repetição e avaliação separada por participante. Consulte [preparação, execução, testes e limitações](../docs/fisioterapia/README.md). O processamento de vídeo exige Python 3.12 e as dependências de `requirements-video.txt`; `requirements-dev.txt` inclui os testes. A instalação original de sinais vitais abaixo continua disponível.

API FastAPI para consultar o catálogo de pacientes, recuperar relatórios de sinais vitais e importar registros do PhysioNet para análise descritiva com suporte de IA.

## Visão geral

A aplicação expõe rotas sob o prefixo `/v1/sinais-vitais` e usa FastAPI para servir:

- listagem de pacientes cadastrados;
- recuperação do relatório JSON mais recente por paciente;
- download do CSV detalhado dos sinais vitais;
- consulta de tabelas de referência por sinal;
- importação e processamento de dados clínicos a partir do PhysioNet;
- análise dos sinais vitais por OpenAI, com geração de status e explicação textual por canal.

O ponto de entrada da aplicação está em `main.py` e a documentação automática fica disponível em:

- `/docs`
- `/openapi.json`

## Requisitos

- Python 3.10+
- Dependências listadas em `requirements.txt`

## Execução local

A partir da raiz do repositório:

```powershell
cd analise-medica-api
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Também é possível iniciar a API a partir da raiz do projeto:

```powershell
uvicorn main:app --app-dir analise-medica-api --reload
```

## Estrutura principal

- `main.py`: criação da aplicação FastAPI e registro do roteador.
- `controller/`: validação das requisições HTTP e mapeamento de erros.
- `services/`: lógica de negócio para localizar pacientes, baixar dados, montar relatórios e persistir arquivos.
- `integrations/`: integrações com PhysioNet e OpenAI.
- `data/`: catálogo de pacientes, tabelas de referência e arquivos gerados pela execução.

## Dados e arquivos gerados

Os arquivos produzidos pela API ficam em `data/` e incluem:

- `data/pacientes.json`: catálogo de pacientes disponíveis para consulta e importação.
- `data/referencias_sinais_vitais.json`: arquivo esperado para tabelas de referência; não está versionado neste checkout.
- `data/<NOME_DO_PACIENTE>/<YYYYMMDD_HHMMSS>/`: diretório com CSV e relatório JSON da execução.

Os arquivos gerados são normalmente ignorados pelo Git, enquanto `data/pacientes.json` e o marcador da pasta são versionados.

## Endpoints

### 1) Listar pacientes

Endpoint:

```http
GET /v1/sinais-vitais/paciente
```

Resposta: lista de pacientes com os campos:

```json
[
  {
    "id": "3000190n",
    "cpf": "12345678900",
    "nome": "Carlos Alberto Lima",
    "idade": 55,
    "genero": "Masculino",
    "prontuario": "Histórico clínico do paciente"
  }
]
```

### 2) Consultar tabela de referência

Endpoint:

```http
GET /v1/sinais-vitais/tabela-referencia
```

Parâmetro opcional:

```http
GET /v1/sinais-vitais/tabela-referencia?sinal=HR
```

Comportamento:

- sem `sinal`: retorna todas as tabelas de referência disponíveis;
- com `sinal`: retorna a tabela do canal solicitado;
- se o sinal não existir, responde com HTTP 404.

### 3) Recuperar relatório de análise

Endpoint:

```http
GET /v1/sinais-vitais/relatorio
```

Parâmetros de consulta:

- `cpf` (opcional)
- `id` (opcional, alias de `id_registro` no código)

Exemplo:

```http
GET /v1/sinais-vitais/relatorio?cpf=12345678900&id=3000190n
```

Regras:

- ao menos um dos parâmetros deve ser informado;
- se ambos forem informados, devem apontar para o mesmo paciente;
- caso não exista relatório, responde com HTTP 404 e a mensagem `Relatório não localizado.`.

### 4) Recuperar CSV detalhado dos sinais vitais

Endpoint:

```http
GET /v1/sinais-vitais/datalhamento
```

Parâmetros de consulta:

- `cpf`
- `id`

Exemplo:

```http
GET /v1/sinais-vitais/datalhamento?cpf=12345678900&id=3000190n
```

Comportamento:

- retorna o CSV mais recente do paciente como anexo;
- se nenhum parâmetro for fornecido, responde com HTTP 422;
- se os identificadores não corresponderem ou o arquivo não existir, responde com HTTP 404.

### 5) Baixar sinais vitais de um paciente

Endpoint:

```http
POST /v1/sinais-vitais/
```

Body:

```json
{
  "id": "3000190n"
}
```

Fluxo:

1. valida se o paciente existe em `data/pacientes.json`;
2. baixa o registro do PhysioNet;
3. salva o CSV em `data/<NOME_DO_PACIENTE>/<YYYYMMDD_HHMMSS>/`;
4. gera o relatório JSON descritivo com estatísticas dos sinais;
5. realiza análise de cada sinal com OpenAI;
6. salva o arquivo `ANALISE_IA_SINAIS_VITAIS.json` no mesmo diretório da execução.

Casos de erro:

- paciente não encontrado: HTTP 404 com `Paciente não localizado`;
- falha de configuração da análise IA: HTTP 503;
- falha na integração com OpenAI: HTTP 502;
- falha ao consultar o PhysioNet: HTTP 502.

## Análise com OpenAI

Antes de usar a rota de importação, configure o arquivo `.env` na pasta `analise-medica-api` com as variáveis:

```env
OPENAI_API_KEY=sua_chave
OPENAI_MODEL=gpt-6-luna
OPENAI_BASE_URL=https://api.openai.com/v1
```

O valor padrão de `OPENAI_MODEL` no código é `gpt-6-luna` e o padrão de `OPENAI_BASE_URL` é `https://api.openai.com/v1`.

Durante a análise, a integração envia para a OpenAI:

- idade;
- sexo;
- histórico médico do cadastro;
- estatísticas resumidas dos sinais vitais.

Não são enviados:

- nome;
- CPF;
- identificador do paciente;
- CSV bruto.

A resposta da IA é informativa e não substitui avaliação profissional. O resultado inclui, para cada canal (`HR`, `SpO2`, `NBPs`, `NBPd`, `PULSE`, `RESP`), um `status` entre `Normal`, `Alterado` ou `Não Conclusivo` e um texto de `analise_ia`.

## Tratamento dos dados e interpolação

O CSV importado passa por normalização de colunas e interpolação de lacunas:

- lacunas numéricas são preenchidas por interpolação linear;
- valores ausentes nas extremidades recebem o valor mais próximo observado;
- sinais sem medição suficiente permanecem vazios;
- colunas como `<nome_do_sinal>__interpolado` marcam os valores estimados.

Esses valores interpolados são exibidos como estimativas e não são considerados nas estatísticas e classificações do relatório final.

## Documentação automática

Com a API em execução, é possível usar:

```text
http://localhost:8000/docs
http://localhost:8000/openapi.json
```

para visualizar a interface Swagger e os metadados da API.
