# Vídeos de fisioterapia — REHAB24-6

Módulo acadêmico integrado à API FastAPI e ao frontend existente. Analisa Ex1 (abdução do braço direito), Ex2 (braços V–W), Ex3 (flexão apoiada na mesa) e Ex4 (abdução de perna). São gravações do próprio dataset, sem upload externo e sem vinculação aos pacientes do PhysioNet.

## Instalação

Use Python 3.12 e execute a partir da raiz do repositório:

```sh
cd analise-medica-api
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-video.lock.txt
```

O lock registra o ambiente completo usado na verificação, incluindo testes. Para instalar somente o conjunto declarado de dependências do módulo, use `requirements-video.txt`; `requirements-dev.txt` inclui pytest/httpx. No Windows, ative com `.venv\Scripts\Activate.ps1`. O módulo de sinais vitais continua podendo iniciar com suas dependências originais em `requirements.txt`; o processamento de vídeo exige as dependências adicionais.

## Preparação para usar os modelos publicados

Os comandos seguintes são executados dentro de `analise-medica-api`, com o ambiente virtual ativo:

```sh
python -m fisioterapia prepare
python -m fisioterapia evaluate
```

O comando `prepare` baixa o pacote de vídeos completo (aproximadamente 2,7 GB) e as anotações, verifica os checksums publicados e extrai Ex1–Ex4. `evaluate` confere a identidade portátil do experimento e exibe as métricas dos classificadores já incluídos no Git. **Não é necessário executar `train` para analisar os vídeos.** É necessário espaço adicional para os vídeos extraídos, o ambiente Python e os caches. Uma interrupção do download deixa um arquivo `.part`, que não é tratado como válido sem a verificação de checksum.

O processamento usa CPU por padrão. Em um Mac compatível, a extração pode ser acelerada com:

```sh
python -m fisioterapia extract --video-id ID --device mps --batch 8
```

Essa escolha é persistida em `data/fisioterapia/runtime.json` e participa da identidade dos caches de postura; **não invalida os classificadores publicados**. Para voltar à CPU, use `--device cpu --batch 1`; o cache de postura do vídeo será recriado quando necessário. Em um host com GPU NVIDIA configurada, é possível usar `--device cuda:0`. Não existe requisito de GPU para iniciar a API.

A página não treina modelos. Ao solicitar a análise de uma gravação, a API extrai sua postura com YOLOv8 Pose se ainda não houver cache válido e usa o Random Forest publicado. Caches válidos evitam nova inferência nos vídeos já processados. Para reproduzir a avaliação inteira a partir dos dados originais, use `python -m fisioterapia extract`, depois `python -m fisioterapia train`; isso recria os 20 modelos e pode demorar. O comando `weights` só é necessário se o arquivo de pesos versionado estiver ausente.

Todos os comandos aceitam `--root CAMINHO` para outro diretório de dados. Para a API usar o mesmo diretório, configure `FISIOTERAPIA_DATA_DIR`. Não misture extração/treinamento com um servidor fazendo análises no mesmo diretório.

## Iniciar a aplicação

Dentro de `analise-medica-api`:

```sh
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

Em outro terminal, a partir da raiz do repositório:

```sh
python3 -m http.server 5500 --bind 127.0.0.1 --directory analise-medica-frontend
```

Abra `http://127.0.0.1:5500/pages/fisioterapia.html`. A URL da API está no `assets/js/config.js` do frontend. O CORS permite as origens locais `localhost` e `127.0.0.1`. Bootstrap e ícones continuam sendo carregados por CDN, como no frontend original; o Chart.js desta página é local.

Selecione exercício, câmera e gravação. Clique em **Analisar vídeo** e acompanhe o andamento. Depois, escolha uma repetição para navegar ao trecho e explorar suas medidas. A página oferece postura sobreposta, gráfico, classificação por repetição, referência oficial separada da predição e download do relatório JSON.

Use um único processo Uvicorn: a fila é local, com um trabalho de visão por vez. Um reinício marca trabalhos interrompidos como falhos; uma nova análise permite tentar novamente. Pedidos repetidos da mesma gravação/modelo reutilizam o resultado válido.

## Método e limites

1. PyAV decodifica todos os frames na ordem de apresentação, verificando timestamps e geometria. A imagem é redimensionada proporcionalmente para lado máximo de 640 pixels antes da conversão de cor, reduzindo o custo de leitura. YOLOv8n Pose extrai os 17 pontos corporais COCO; os pontos normalizados são associados às dimensões originais para calcular as medidas. O sistema acompanha a pessoa principal por continuidade espacial e rejeita associação ambígua. Nenhum frame é descartado por amostragem.
2. Os intervalos de repetição são fornecidos por `Segmentation.csv`. Esta versão não descobre automaticamente as repetições ou o exercício.
3. As medidas usam dimensões reais da imagem, ângulos 2D e proporções normalizadas pelo tronco. Coordenadas de baixa confiança não são interpretadas como postura correta. Exige-se confiança mínima 0,5 e cobertura de pelo menos 60% dos frames com medidas essenciais.
4. Um Random Forest é treinado por exercício. A avaliação usa cinco grupos por participante; todas as câmeras e repetições de uma pessoa ficam juntas. Preenchimento de features é ajustado somente no treino.
5. Para analisar uma gravação do dataset, usa-se o modelo do grupo que excluiu aquele participante. A predição não recebe os rótulos de correção. Os rótulos são usados apenas no treinamento e na comparação posterior.

A avaliação publica métricas sobre as repetições classificáveis e informa separadamente cobertura e não conclusivos por rótulo. Também calcula `recall_incorrect_all`: execuções incorretas detectadas divididas por todas as execuções incorretas, incluindo as não conclusivas no denominador. Assim, baixa visibilidade não desaparece da avaliação de alcance do detector.

`Correto` e `Incorreto` são classes acadêmicas aprendidas do dataset. `Não conclusivo` significa que faltou postura confiável. Ângulos projetados em 2D dependem da câmera; vistas laterais podem ocultar articulações. O dataset não fornece tipo ou gravidade do erro, portanto o relatório não atribui causas clínicas ou prescreve correções. O módulo não gera diagnóstico.

O relatório informa que a segmentação é oficial. Os frames originais são preservados. A conferência dos arquivos reais encontrou `first_frame=1` e, em PM_045 e PM_103 nas duas câmeras, `last_frame` igual ao número total de frames. Isso é compatível com contagem de origem 1 e final inclusivo. O adaptador registra essa evidência e converte para índices internos de origem 0: `[first_frame-1:last_frame]`, com intervalo de reprodução `[(first_frame-1)/30, last_frame/30)`. O dicionário público não declara explicitamente a origem; essa interpretação é fundamentada nas bordas dos arquivos reais, não apresentada como uma declaração textual dos autores. Intervalos além dessas bordas continuam sendo rejeitados.

`mocap_erroneous` indica falha na captura de marcadores, não execução incorreta. Os esqueletos oficiais não substituem a extração feita pelo YOLO neste módulo.

## API

| Método | Rota | Finalidade |
|---|---|---|
| GET | `/v1/fisioterapia/catalogo` | Exercícios e gravações disponíveis, sem caminhos locais ou rótulos de referência |
| GET | `/v1/fisioterapia/videos/{video_id}` | Vídeo catalogado, com suporte a Range/busca temporal |
| POST | `/v1/fisioterapia/analises` | Criar/reutilizar análise com corpo `{"video_id":"ID"}`; retorna 202 |
| GET | `/v1/fisioterapia/analises/{id}` | Estado, progresso, eventual erro e URLs do resultado |
| GET | `/v1/fisioterapia/analises/{id}/relatorio` | Relatório JSON para download |
| GET | `/v1/fisioterapia/analises/{id}/pose` | Pontos corporais normalizados e FPS para sobreposição |

Erros de configuração usam HTTP 503, identificadores inexistentes usam 404 e relatório ainda indisponível usa 409. Entradas malformadas são rejeitadas com 422. Não é permitido fornecer caminhos de arquivos ou URLs de vídeos.

## Testes

```sh
# Dentro de analise-medica-api, ambiente ativo:
python -m pytest -q
```

Os testes rápidos usam geometria conhecida, mídia sintética, arquivos temporários e substituição somente da inferência lenta nos testes do serviço. Incluem divisão por participante, predição sem rótulos, cache, falha/reinício, Range/CORS e regressão das rotas de sinais vitais. Não precisam de credenciais OpenAI, PhysioNet ou Azure.

Na raiz do repositório, para testes de interface:

```sh
npm ci
npx playwright install chromium
npm run test:e2e
```

Esses testes exercitam a página real com respostas controladas da API, incluindo resultado não conclusivo, download, falha e layout estreito. A verificação com vídeos, YOLO e API reais é registrada separadamente dos testes controlados; nenhum teste sintético comprova a qualidade do classificador.

Com o dataset processado, os classificadores treinados e a API em `127.0.0.1:8000`, inclua o cenário real dos quatro exercícios:

```sh
FIAP_REAL_API=1 npm run test:e2e
```

O cenário confere reprodução, navegação por repetição, predição com participante excluído do treino e conteúdo do relatório baixado. As capturas ficam em `playwright-output/`, ignorado pelo Git. Consulte as métricas e evidências desta execução em [resultados.md](resultados.md) e o escopo restante da entrega em [pendencias-fase4.md](pendencias-fase4.md).

## Artefatos e reprodução

Os pesos YOLO, os 20 classificadores treinados e seus manifestos foram incluídos no Git, nos caminhos originais de `analise-medica-api/data/fisioterapia/`. Os demais dados continuam gerados localmente:

- `downloads/`: fontes, metadados e checksums do Zenodo;
- `videos/` e `catalog.json`: mídia preparada e associação das gravações;
- `models/yolov8n-pose.pt`: pesos oficiais de pose, versionados;
- `poses/`: postura por vídeo e metadados de cache;
- `experiments/`: classificadores por exercício/grupo, métricas e predições OOF, versionados;
- `experiment.json`: manifesto do experimento ativo, versionado;
- `jobs/` e `reports/`: tarefas e resultados da interface.

O manifesto publicado contém uma identidade de implantação baseada no catálogo, hashes declarados das mídias, anotações, pesos, método de pose, esquema de features e versão do scikit-learn. Datas locais dos arquivos, dispositivo e lote não participam dessa identidade. Assim, depois de instalar as dependências e executar `prepare`, os classificadores versionados podem ser usados sem novo treino. O vídeo selecionado ainda é conferido por hash antes da inferência, e o modelo escolhido é conferido por hash antes de ser carregado. Clonar o repositório não baixa os vídeos nem instala dependências.

Os modelos joblib são artefatos produzidos por este projeto, não entradas enviadas por usuários. Os hashes são conferidos antes de carregá-los. Mudanças nos dados, pesos ou método podem invalidar o experimento e exigir nova preparação ou treino; mudanças de dispositivo/lote apenas recriam o cache de pose. A identidade do cache inclui Ultralytics, PyTorch, OpenCV e política de rastreamento. Remover ou alterar um cache de postura invalida o resultado reutilizado. Após perda de associação por mais de 15 frames, o rastreador não assume que uma pessoa reaparecida é o mesmo participante; os frames restantes ficam sem postura associada.

## Fonte e licença

[REHAB24-6, registro 13305826](https://zenodo.org/records/13305826), versão v1. Uso para pesquisa acadêmica ou de organizações sem fins lucrativos, não comercial, conforme as condições publicadas. Uso comercial requer contato com os autores. Não redistribuímos os vídeos no Git.

Referência: Černek, A.; Sedmidubsky, J.; Budikova, P. **REHAB24-6: Physical Therapy Dataset for Analyzing Pose Estimation Methods.** SISAP, Springer, 2024.

[Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8/) fornece a variante de pose utilizada. Chart.js 4.4.7 é distribuído sob licença MIT, preservada no cabeçalho do arquivo local.
