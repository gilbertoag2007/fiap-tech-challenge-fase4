# Prontuário Digital — Frontend

Frontend estático do sistema de acompanhamento e análise de sinais vitais. A interface consulta a API FastAPI, permite selecionar pacientes, visualizar relatórios e analisar gráficos por sinal vital.

## Visão geral

A aplicação é composta por:

- página inicial (`index.html`) com apresentação do sistema;
- página de monitoramento (`pages/sinais-vitais.html`);
- estilos em `assets/css/style.css`;
- configurações de API em `assets/js/config.js`;
- serviços e componentes em `assets/js/services/` e `assets/js/components/`.

A página de sinais vitais busca os pacientes em `/v1/sinais-vitais/paciente`, carrega o CSV detalhado em `/v1/sinais-vitais/datalhamento`, consulta o relatório em `/v1/sinais-vitais/relatorio` e lê as tabelas de referência em `/v1/sinais-vitais/tabela-referencia`.

## Requisitos

- Python 3.10+
- servidor da API em execução na porta 8000
- acesso à internet para baixar Bootstrap, Bootstrap Icons, Axios, Papa Parse e Chart.js por CDN

## Executar localmente

Inicie a API em um terminal, a partir da pasta `analise-medica-api`:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Em outro terminal, execute o frontend estático na pasta `analise-medica-frontend`:

```powershell
python -m http.server 5500 --bind 127.0.0.1
```

Acesse:

```text
http://127.0.0.1:5500
```

## Configuração da API

O arquivo `assets/js/config.js` define as rotas usadas pelo frontend:

```js
window.API_BASE_URL = "http://127.0.0.1:8000";
window.PATIENTS_ENDPOINT = "/v1/sinais-vitais/paciente";
window.VITAL_SIGNS_ENDPOINT = "/v1/sinais-vitais/datalhamento";
window.VITAL_SIGNS_REPORT_ENDPOINT = "/v1/sinais-vitais/relatorio";
window.VITAL_SIGNS_REFERENCE_ENDPOINT = "/v1/sinais-vitais/tabela-referencia";
```

Se a API estiver em outra porta ou origem, ajuste esses valores antes de abrir o frontend.

A API aceita requisições locais do tipo `localhost` e `127.0.0.1` por padrão; se necessário, ajuste o CORS em `analise-medica-api/main.py`.

## Estrutura principal

```text
analise-medica-frontend/
├── index.html
├── pages/
│   └── sinais-vitais.html
├── assets/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js
│       ├── config.js
│       ├── components/
│       │   ├── grafico.js
│       │   └── paciente.js
│       ├── pages/
│       │   └── sinais-vitais.js
│       └── services/
│           ├── api.js
│           ├── paciente.service.js
│           └── sinais-vitais.service.js
```

## Funcionalidades atuais

### Página inicial

A landing page apresenta:

- nome do sistema;
- descrição do contexto clínico;
- navegação para a área de monitoramento;
- rodapé com identidade visual do produto.

### Seleção de paciente

Na página `pages/sinais-vitais.html`, o usuário pode:

- listar pacientes vindos da API;
- pesquisar por nome, CPF ou identificador;
- selecionar um paciente em um dropdown;
- visualizar identificação e dados cadastrais;
- receber mensagens de carregamento, erro e ausência de resultados.

### Monitoramento de sinais vitais

Ao selecionar um paciente, o frontend:

- carrega o relatório JSON completo em `/v1/sinais-vitais/relatorio`;
- carrega o CSV detalhado do paciente em `/v1/sinais-vitais/datalhamento`;
- analisa os dados em CSV e extrai os sinais vitais;
- renderiza gráficos do tipo:
  - HR
  - SpO2
  - NBPs
  - NBPd
  - PULSE
  - RESP
- mostra status/observações da análise com inteligência artificial quando disponíveis;
- exibe uma tabela de referência para cada sinal;
- identifica valores interpolados e marca estimativas no tooltip/observações do gráfico.

### Parsing do CSV

O frontend reconhece arquivos CSV com cabeçalhos como:

- `tempo_segundos`
- `HR`
- `PULSE`
- `NBP Sys`
- `NBP Dias`
- `RESP`
- `SpO2`

Também trata:

- delimitadores `,` e `;`;
- valores vazios em colunas numéricas;
- timestamps em `AAAA-MM-DD HH:MM:SS.ffffff`;
- linhas sem tempo válido, que são ignoradas;
- valores interpolados sinalizados como estimativas.

## Fluxo de dados

1. O usuário escolhe um paciente na tela.
2. O frontend consulta `/v1/sinais-vitais/paciente` para montar a lista.
3. O serviço de sinais vitais solicita o CSV do paciente com `id` como parâmetro.
4. O frontend lê o CSV e cria os gráficos em tempo real.
5. O relatório de análise é consultado para preencher resumos, status e descrições por sinal.
6. A tabela de referência é consultada por sinal para mostrar faixas de normalidade.

## Observações

- O frontend é estático e depende de um backend válido para funcionar.
- Não há build step nem bundler; tudo é servido diretamente pelo navegador.
- O visual depende da carga correta dos arquivos em CDN.
- Em caso de erro de API, a interface mostra alertas amigáveis sem quebrar a página.

## Documentação automática

Após iniciar o servidor estático, a interface web fica disponível em:

```text
http://127.0.0.1:5500
```

A aplicação principal de sinal vitals fica em:

```text
http://127.0.0.1:5500/pages/sinais-vitais.html
```
