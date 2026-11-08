# Prontuário Digital — Frontend

## Executar localmente

Inicie a API em um terminal, a partir da pasta `analise-medica-api`:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Em outro terminal, inicie o servidor estático na pasta `analise-medica-frontend`:

```powershell
python -m http.server 5500 --bind 127.0.0.1
```

Acesse `http://127.0.0.1:5500`. O servidor estático usa o módulo padrão do
Python e não requer dependências frontend. Bootstrap, Bootstrap Icons e Axios
são carregados por CDN, portanto é necessária conexão à internet. Papa Parse e
Chart.js também são carregados por CDN na página de sinais vitais.

A API permite requisições GET de origens locais (`localhost` e `127.0.0.1`)
para o desenvolvimento. Para usar outra origem, ajuste a configuração CORS em
`../analise-medica-api/main.py`.

## Configuração da API

Em `assets/js/config.js`, altere `API_BASE_URL` para o endereço base da API e
`PATIENTS_ENDPOINT` para a rota que retorna a lista de pacientes. A configuração
atual consulta `http://127.0.0.1:8000/v1/sinais-vitais/paciente`.

O endpoint de CSV é configurado separadamente em `VITAL_SIGNS_ENDPOINT` e usa
`GET /v1/sinais-vitais/datalhamento?id=<identificador>`. Esse caminho e o
parâmetro `id` correspondem ao contrato atual da API. O endpoint aceita também
`cpf`, caso seja necessário adaptar o serviço para esse identificador.

## Formato do CSV

O parser reconhece os cabeçalhos `tempo_segundos`, `HR`, `PULSE`, `NBP Sys`,
`NBP Dias`, `RESP` e `SpO2`, detectando o delimitador vírgula ou ponto e vírgula.
Campos numéricos vazios permanecem sem valor; linhas sem tempo válido são
ignoradas. A coluna `tempo_segundos` aceita segundos decorridos em CSVs antigos
ou timestamps no formato `AAAA-MM-DD HH:MM:SS.ffffff`. Nos CSVs com timestamp,
o tooltip mostra a data e hora do registro em `dd/mm/yyyy hh:mm:ss` ao passar
o mouse; o eixo continua exibindo o tempo decorrido desde o início do exame.
Valores interpolados são identificados no tooltip como estimativas.
