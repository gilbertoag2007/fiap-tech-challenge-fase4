# Prontuário Digital — FIAP Tech Challenge, Fase 4

Projeto acadêmico com duas frentes implementadas: consulta e análise descritiva de sinais vitais obtidos do PhysioNet; e análise de vídeos de quatro exercícios de fisioterapia do REHAB24-6. A interface é HTML/JavaScript e a API é FastAPI. O sistema **ainda não conclui todos os requisitos da Fase 4**: áudio/Azure, detecção temporal de anomalias clínicas, prescrições, movimentação durante internação, alertas e fusão multimodal permanecem pendentes.

Leia o [relatório técnico completo](docs/relatorio-tecnico-fase4.md) ([PDF](docs/relatorio-tecnico-fase4.pdf)) para arquitetura, métodos, resultados, rastreabilidade ao enunciado e limites. Os [resultados detalhados de vídeo](docs/fisioterapia/resultados.md) incluem matrizes de confusão e cobertura.

## O que funciona hoje

| Área | Implementação | Estado da validação |
|---|---|---|
| Sinais vitais | Importação WFDB de um registro do catálogo, interpolação sinalizada, estatísticas de seis canais, análise informativa via OpenAI, CSV e JSON | Rotas e inicialização cobertas por testes de regressão; integração real PhysioNet/OpenAI e acerto clínico não foram avaliados neste repositório |
| Fisioterapia | Ex1–Ex4 do REHAB24-6, duas câmeras, YOLOv8n Pose pré-treinado, medidas 2D, Random Forest por exercício, relatório por repetição e visualização | 94 vídeos/260.750 frames processados; avaliação por participante excluído do treino; 58 testes Python e 4 de navegador passaram nas execuções registradas |

No vídeo, a classificação é `Correto`, `Incorreto` ou `Não conclusivo`. A balanced accuracy medida foi 64,14% / 64,59% / **45,45%** / 73,40% para Ex1–Ex4, com cobertura 75,84% / 79,09% / 88,32% / 100%. O Ex3 tem qualidade insuficiente. O resultado é acadêmico, sem validação clínica.

## Estrutura

```text
analise-medica-api/
  main.py                         FastAPI, CORS e ciclo de vida
  controller/                      Rotas de sinais vitais e fisioterapia
  services/                        Relatórios e orquestração de sinais vitais
  integrations/                    PhysioNet/WFDB e OpenAI
  fisioterapia/                    Dataset, pose, medidas, treino e tarefas
  tests/                            Testes Python e regressão
  data/pacientes.json               Catálogo local de registros para sinais
  data/fisioterapia/models/         Pesos YOLOv8 Pose versionados
  data/fisioterapia/experiments/    20 classificadores e manifestos versionados
analise-medica-frontend/
  index.html                        Página inicial
  pages/sinais-vitais.html          Consulta de sinais vitais
  pages/fisioterapia.html           Análise de vídeos
  assets/                           Estilos, serviços e scripts da interface
docs/                               Relatório técnico, resultados e guias
 tests/browser/                     Testes de interface com Playwright
```

Os voluntários do REHAB24-6 e os registros do PhysioNet são fontes independentes. O projeto não estabelece correspondência entre eles.

## Requisitos para executar

- Python **3.12** para o ambiente integrado de vídeo; Python 3.10+ é declarado para a base de sinais isolada.
- Conexão de rede para preparar os vídeos do Zenodo e usar PhysioNet/OpenAI. A página de sinais também carrega bibliotecas de CDN.
- Espaço para baixar o ZIP de vídeos (~2,5 GB), extrair os vídeos selecionados (~1,7 GB), instalar dependências e criar caches. CPU funciona para vídeo; MPS/CUDA são opcionais.
- Uma chave OpenAI configurada em `analise-medica-api/.env` **somente** para executar o POST de importação/análise de sinais vitais. A consulta de relatórios existentes e o módulo de vídeo não exigem essa chave.

### API integrada

A partir da raiz do repositório, em um terminal POSIX:

```sh
cd analise-medica-api
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-video.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

No Windows, siga a [sequência completa em PowerShell](#windows-powershell) para instalar, preparar os vídeos e iniciar a API. `requirements-video.txt` fixa as versões das dependências principais do módulo, sem prender a instalação a um sistema operacional. Para executar apenas a API de sinais, `requirements.txt` contém as dependências originais. A API pode iniciar sem as bibliotecas opcionais de visão, mas a análise de vídeo precisa delas.

O Swagger fica em `http://127.0.0.1:8000/docs` e o esquema em `/openapi.json`.

### Frontend

Em outro terminal, na raiz:

```sh
python3 -m http.server 5500 --bind 127.0.0.1 --directory analise-medica-frontend
```

Abra `http://127.0.0.1:5500/`, `/pages/sinais-vitais.html` ou `/pages/fisioterapia.html`. A URL da API está em `analise-medica-frontend/assets/js/config.js`; as origens HTTP(S) locais `localhost`/`127.0.0.1` são aceitas pelo CORS. Use um processo Uvicorn para a fila local de vídeo.

## Preparar sinais vitais

Copie `analise-medica-api/.env.example` para `analise-medica-api/.env`, preencha `OPENAI_API_KEY` e confira `OPENAI_MODEL` e `OPENAI_BASE_URL` disponíveis na sua conta. **Não envie o `.env` ao Git.** O código exige a chave no POST de importação e pode fazer uma chamada paga ao serviço configurado.

O catálogo versionado `data/pacientes.json` associa cadastros locais a IDs/diretórios WFDB. A tela de sinais **consulta** CSVs e relatórios já gerados: ela não executa a importação. Para gerar um relatório, com API e credenciais prontos:

```sh
curl -X POST http://127.0.0.1:8000/v1/sinais-vitais/ \
  -H 'Content-Type: application/json' \
  -d '{"id":"3000190n"}'
```

Então abra a página ou consulte `GET /v1/sinais-vitais/relatorio?id=3000190n`. A importação lê as **primeiras 600 amostras**, cuja duração depende da frequência do registro. Os timestamps da coluna `tempo_segundos` são datas sintéticas, não horários originais do PhysioNet. Não há CSV/relatório de sinais gerado no clone. A tabela de referências espera `data/referencias_sinais_vitais.json`, que **não está no checkout**; sem ele, a coleção vem vazia e buscas por canal retornam 404.

## Preparar fisioterapia

Os pesos oficiais YOLOv8 Pose e 20 classificadores experimentais já estão versionados. Para usar esses modelos em outra máquina, **não é necessário treinar novamente**. Os vídeos e as anotações são obtidos do Zenodo; dentro de `analise-medica-api`, com `.venv` ativo, execute:

```sh
python -m fisioterapia prepare
python -m fisioterapia evaluate
```

`prepare` baixa e verifica o ZIP do [REHAB24-6](https://zenodo.org/records/13305826), extrai Ex1–Ex4 e cria o catálogo. `evaluate` confere a compatibilidade dos dados, pesos e dependências com os modelos publicados. Em seguida, inicie API e frontend e selecione uma gravação: o YOLO gera a postura daquele vídeo na primeira análise e a classificação usa o modelo já versionado. A inferência pode demorar na CPU; análises posteriores reutilizam o cache. `extract` para todos os vídeos e `train` são opcionais para reproduzir o experimento, não passos de instalação. Consulte o [guia de vídeo](docs/fisioterapia/README.md) para parâmetros e integridade.

### Windows PowerShell

Na raiz do repositório, com Python 3.12 instalado, execute os comandos abaixo em um terminal. A preparação baixa o pacote de vídeos (~2,5 GB) e extrai os exercícios selecionados (~1,7 GB); aguarde a conclusão antes de abrir a página.

```powershell
cd .\analise-medica-api
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-video.txt
python -m fisioterapia prepare
# Opcional: confere o experimento publicado e mostra métricas já salvas.
python -m fisioterapia evaluate
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

Se uma instalação anterior parou com `RuntimeError: uvloop does not support Windows`, dentro de `analise-medica-api` execute `python -m pip install -r requirements-video.txt` no mesmo ambiente virtual; não é necessário instalar `uvloop` nem recriar o ambiente. O comando `evaluate` apenas confere a compatibilidade dos dados preparados com o experimento publicado e mostra métricas já salvas: é opcional para usar a aplicação.

Em um segundo terminal, na raiz do repositório, inicie o frontend com `py -3.12 -m http.server 5500 --bind 127.0.0.1 --directory analise-medica-frontend`. Quando `prepare` terminar, a página deve listar os exercícios; não é necessário executar `train`. Se aparecer **“Dataset não preparado”**, verifique no terminal da API o diretório usado e se o catálogo existe:

```powershell
python -c "from fisioterapia.config import root_path; print(root_path()); print((root_path() / 'catalog.json').is_file())"
```

O resultado esperado é o caminho `analise-medica-api\data\fisioterapia` seguido de `True`. Se aparecer `False` depois de `prepare` concluir, confira se o comando e a API usam o mesmo `FISIOTERAPIA_DATA_DIR`; ao mudar essa variável, reinicie a API.

Abra `http://127.0.0.1:5500/pages/fisioterapia.html`. Se a página piscar e a API receber vários `GET /v1/fisioterapia/catalogo` após clicar em **Analisar vídeo**, pare o **Live Server** do VS Code e use o servidor Python acima. Durante a análise, a API atualiza arquivos de progresso dentro do repositório; o Live Server pode interpretar essas mudanças como motivo para recarregar a página. Pare o Live Server antes de iniciar o servidor Python, pois ambos podem tentar usar a porta 5500. A URL correta do servidor Python não inclui `/analise-medica-frontend/`.

Se `prepare` informar **“checksum inválido”** em um arquivo `.part`, atualize esta branch e execute o comando novamente. A preparação descarta arquivos temporários inválidos e lê corretamente respostas HTTP comprimidas; a conferência de checksum continua obrigatória.

O sistema aceita apenas as gravações catalogadas, das câmeras 17 e 18, e usa a segmentação oficial das repetições. Não há upload de vídeos novos ou descoberta automática do exercício. O YOLOv8 Pose extrai pontos corporais; o Random Forest treinado pelo projeto usa as medidas derivadas para prever correção.

## API principal

| Método | Rota | Uso |
|---|---|---|
| GET | `/v1/sinais-vitais/paciente` | Catálogo local de pacientes/registros |
| POST | `/v1/sinais-vitais/` | Importar WFDB e gerar análise com OpenAI; corpo `{"id":"3000190n"}` |
| GET | `/v1/sinais-vitais/relatorio?id=...` | Último relatório existente |
| GET | `/v1/sinais-vitais/datalhamento?id=...` | CSV existente (grafia da rota no código) |
| GET | `/v1/sinais-vitais/tabela-referencia?sinal=HR` | Referência, se arquivo local existir |
| GET | `/v1/fisioterapia/catalogo` | Exercícios, vídeos e câmeras preparados |
| GET | `/v1/fisioterapia/videos/{video_id}` | MP4 catalogado com suporte a Range |
| POST | `/v1/fisioterapia/analises` | Iniciar/reutilizar análise; corpo `{"video_id":"ID_DO_CATALOGO"}` |
| GET | `/v1/fisioterapia/analises/{job_id}` | Estado e progresso |
| GET | `/v1/fisioterapia/analises/{job_id}/relatorio` | Relatório JSON |
| GET | `/v1/fisioterapia/analises/{job_id}/pose` | Pontos corporais por frame |

As rotas não têm autenticação; execute localmente. Há dados cadastrais no catálogo. O relatório completo descreve contratos, persistência e limites de cada módulo.

## Testes e evidências

Na pasta da API, com dependências de desenvolvimento (`requirements-dev.txt` ou lock):

```sh
python -m pytest -q
```

Na raiz, com Node.js e Chromium do Playwright instalados:

```sh
npm ci
npx playwright install chromium
npm run test:e2e
```

O último comando executa cenários controlados. Para incluir o cenário real dos quatro exercícios, prepare os dados/modelos, inicie a API local e execute `FIAP_REAL_API=1 npm run test:e2e` (POSIX). A verificação atual foi **58 testes Python aprovados**; a execução registrada de navegador teve quatro testes aprovados. Houve dois avisos upstream WFDB/pandas. Esses testes não medem acerto clínico da análise OpenAI nem validam os requisitos multimodais pendentes. Veja [resultados e matrizes](docs/fisioterapia/resultados.md).

## Licença de dados e limites

[REHAB24-6 v1](https://zenodo.org/records/13305826) é disponibilizado para pesquisa acadêmica/não comercial segundo as condições dos autores; não redistribuímos os vídeos no Git. Consulte também os termos do [PhysioNet](https://physionet.org/) para a fonte WFDB. O software é demonstrador acadêmico e não foi validado para decisões assistenciais. A entrega ainda precisa de áudio/Azure, anomalias temporais/prescrições/movimentação, alertas, integração multimodal e vídeo demonstrativo final. O [relatório técnico](docs/relatorio-tecnico-fase4.md) detalha a matriz de requisitos e as evidências disponíveis.
