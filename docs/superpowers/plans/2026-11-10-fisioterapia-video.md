# Fisioterapia por vídeo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Analisar os vídeos Ex1–Ex4 do REHAB24-6 com YOLOv8 Pose e classificação avaliada por participante, integrando resultados ao frontend.

**Architecture:** Pacote `fisioterapia` isolado das integrações clínicas atuais, com preparação por CLI, extração cacheada, treinamento agrupado e serviço de tarefas locais. API oferece catálogo, vídeo, progresso e relatório. Frontend estático consome essa API e sincroniza reprodução, pontos corporais e repetições.

**Tech Stack:** Python 3.12, FastAPI, NumPy, OpenCV, Ultralytics/YOLOv8n-pose, scikit-learn/Random Forest, pytest/httpx; HTML/Bootstrap/JavaScript/Chart.js e Playwright para verificação.

**Ajuste técnico medido durante execução:** PyAV 16.0.1 foi incluído na leitura sequencial para redimensionar antes da conversão BGR, mantendo todos os frames e validando PTS. O decoder e sua versão fazem parte da identidade da engine. Os testes adicionais estão em `tests/test_fisioterapia_video.py`; OpenCV permanece na preparação e inspeção da mídia.

**Spec:** `docs/superpowers/specs/2026-11-10-fisioterapia-video-design.md` (aprovado pelo usuário em 10/11/2026).

## Global Constraints

- Somente Ex1, Ex2, Ex3 e Ex4 do registro Zenodo 13305826; sem upload externo e sem vincular participantes a pacientes PhysioNet.
- Pesos `yolov8n-pose.pt`; intervalos oficiais a 30 FPS; qualidade mínima dos pontos 0,5 e cobertura mínima 60%.
- Cinco grupos por participante; ambas as câmeras da mesma pessoa sempre no mesmo grupo. Nenhum identificador ou rótulo é feature.
- Resultados da demonstração gerados pelo modelo que excluiu o participante do treinamento.
- Dados, modelos e caches locais ignorados pelo Git; relatório sem chamadas de LLM ou Azure.
- Servidor local com um processo e um executor de um trabalho por vez; preservar rotas de sinais vitais.

## Review Focus

- Vídeos e resultados antigos: hashes de mídia, pesos, features e modelos devem invalidar cache.
- Reinício/concorrência: trabalhos interrompidos falham explicitamente; pedidos duplicados não duplicam processamento.
- Pessoas extras e oclusões: acompanhar participante com continuidade, rejeitar associação ambígua e informar cobertura.
- Vazamento: grupos, câmeras, rótulos e transformações devem permanecer separados durante ajuste e demonstração.
- Caminhos, frames e vídeo: restringir caminhos ao catálogo; conferir FPS/bordas e oferecer busca temporal HTTP.

## Estrutura e contratos

- `analise-medica-api/fisioterapia/config.py`: configuração, hashes e gravação JSON atômica.
- `dataset.py`: download verificado, extração segura, importação do CSV e catálogo. `prepare(root: Path) -> dict`; `load_catalog(root: Path) -> dict`; `video_path(root: Path, video: dict) -> Path`.
- `features.py`: `repetition_features(points: np.ndarray, exercise: int) -> dict`, entrada `[frames,17,3]` (x/y normalizados pela imagem e confiança), saída `features`, `coverage`, `series`, `reason`.
- `pose.py`: `extract_pose(root: Path, video: dict, progress: Callable | None = None) -> dict`; coordenadas por frame e metadados/versionamento.
- `training.py`: `train(root: Path) -> dict`, `predict_repetitions(root: Path, video: dict, pose: dict) -> list[dict]`, métricas agregadas e modelos por grupo.
- `jobs.py`: `AnalysisService(root: Path, runner: Callable | None = None)`, catálogo, `create(video_id: str) -> dict`, `get(job_id: str) -> dict`, `result(job_id: str) -> dict`, ciclo de vida do executor.
- `controller/fisioterapia_controller.py`: roteador `/v1/fisioterapia`; `GET /catalogo`, `GET /videos/{video_id}`, `POST /analises` com `{video_id}`, `GET /analises/{id}`, `GET /analises/{id}/relatorio`, `GET /analises/{id}/pose`.
- `fisioterapia/__main__.py`: comandos `prepare`, `extract`, `train`, `evaluate`; argumentos `--root`, `--video-id` para limitar extração técnica, sem reduzir silenciosamente a avaliação final.
- `analise-medica-frontend/pages/fisioterapia.html`, `assets/js/pages/fisioterapia.js`, `assets/js/services/fisioterapia.service.js`, estilos adicionais em `assets/css/style.css`.
- `analise-medica-api/tests/test_fisioterapia_*.py`: testes unitários/API/experimento; `tests/test_sinais_vitais_regression.py`: consultas sem serviços externos.
- `docs/fisioterapia/`: execução reproduzível, resultados medidos e pendências da entrega geral.

### Task 1: Ambiente e dataset validado

**Files:** criar `fisioterapia/config.py`, `dataset.py`, `tests/test_fisioterapia_dataset.py`, `pytest.ini`, `requirements-video.txt`, `requirements-dev.txt`; modificar README.
**Interfaces:** produz catálogo com `videos` (id opaco, exercise_id, person_id, camera, relative_path, sha256, fps, width, height, frame_count, repetitions). Repetições preservam campos originais, com índices internos explicitamente documentados.

- [x] Escrever testes para ZIP com caminho perigoso, checksum inválido, registro/câmera ambígua, FPS incompatível, intervalo fora do vídeo, catálogo Ex1–Ex4 e resolução segura de caminho.
- [x] Rodar `.venv/bin/python -m pytest tests/test_fisioterapia_dataset.py -q`; esperado: falha por implementação ausente.
- [x] Implementar download com arquivo `.part`, checksum e rename; extração segura; parsing CSV validado; manifesto e erros úteis. Validar num vídeo real a conversão dos frames, registrando convenção no manifesto/documentação.
- [x] Rodar os testes; esperado: todos passam. Preparar dataset real e confirmar contagens/FPS sem carregar vídeos inteiros em memória.
- [x] Registrar evidência e alterações no ledger; commit local se permitido, sem push.

### Task 2: Pose e medidas dos quatro exercícios

**Files:** criar `features.py`, `pose.py`, `tests/test_fisioterapia_features.py`, `tests/test_fisioterapia_pose.py`.
**Interfaces:** consome catálogo; produz arrays `[frames,17,3]`, metadados de cache, features e séries com `null` para medidas indisponíveis. Geometria deve usar dimensões reais antes de calcular ângulos.

- [x] Escrever testes com ângulos conhecidos, escala corporal, coordenadas degeneradas, ausência de pessoa, confiança baixa, cobertura exatamente no limite e interrupção da identidade. Remover confiança de um ponto essencial deve tornar a medida indisponível.
- [x] Rodar os testes; esperado: falha por funções ausentes.
- [x] Implementar geometria por exercício; quantis 10/50/90, média, desvio, amplitude e média de diferenças absolutas consecutivas; feature order fixo e versionado. Sem preencher lacunas longas ou classificar frames sem evidência.
- [x] Implementar YOLOv8n-pose streaming, associação espacial conservadora e cache invalidado por mídia/pesos/configuração. CPU como padrão. Não usar `correctness` nesta camada.
- [x] Rodar testes; esperado: passam. Extrair um vídeo real por exercício e conferir imagens de pose, cobertura e timestamps.
- [x] Registrar evidência e alterações no ledger; commit local se permitido.

### Task 3: Classificação e avaliação agrupada

**Files:** criar `training.py`, `__main__.py`, `tests/test_fisioterapia_training.py`.
**Interfaces:** consome apenas features e metadados para agrupamento; produz modelos por exercício/grupo, métricas e predições `Correto`/`Incorreto`/`Não conclusivo` com cobertura/medidas. Associação de grupo é persistida.

- [x] Escrever testes para câmeras no mesmo grupo, pessoas disjuntas, predição sem rótulo, falha de classes insuficientes, métricas/coverage e seleção do modelo que excluiu a pessoa. Mudança dos pesos ou features deve invalidar o experimento.
- [x] Rodar testes; esperado: falha por treinamento ausente.
- [x] Implementar `GroupKFold(n_splits=5)` determinístico e RandomForest (`n_estimators=300`, `min_samples_leaf=2`, `class_weight='balanced'`, `random_state=42`, `n_jobs=-1`). Imputação pela mediana dentro de cada treino; nenhum ajuste pelo teste. Registrar features, versões e hashes.
- [x] Produzir métricas OOF e baseline majoritário por exercício e câmera, cobertura e contagem de rejeitados; treino com ambas as classes necessário. Salvar modelos e manifesto de exclusão.
- [x] Rodar testes; esperado: passam. Extrair todo Ex1–Ex4 nas duas câmeras, treinar e avaliar; registrar tempos, falhas e qualidade sem prometer métricas antecipadas.
- [x] Registrar evidência e alterações no ledger; commit local se permitido.

### Task 4: Tarefas, relatório e API

**Files:** criar `jobs.py`, `controller/fisioterapia_controller.py`, `tests/test_fisioterapia_api.py`; modificar `main.py`.
**Interfaces:** consome contratos anteriores; endpoints definidos acima. POST retorna 202 com `id`, `status`, `progress`, `video_id`. Consulta inclui `error` em falha e `report_url`/`pose_url` após conclusão.

- [x] Escrever testes do fluxo real com runner substituindo somente visão lenta: duplicata, cache obsoleto, falha, retomada após reinício, identificação inexistente, caminhos inválidos, relatório indisponível, vídeo com Range e CORS POST. Testar consultas atuais de sinais vitais sem rede.
- [x] Rodar testes; esperado: falha pelas rotas ausentes.
- [x] Implementar execução serial fora do atendimento HTTP, persistência atômica, estados e reutilização por identidade completa. Relatório contém predição separada de rótulo oficial, métricas medidas, limites e intervalos oficiais; ausência de recursos retorna configuração inválida, nunca sucesso vazio.
- [x] Registrar roteador e ciclo de vida; permitir GET/POST e Content-Type no CORS local.
- [x] Rodar suite completa; esperado: passa sem rede e sem chaves externas.
- [x] Registrar evidência e alterações no ledger; commit local se permitido.

### Task 5: Interface integrada

**Files:** criar página, serviço e JS de fisioterapia; modificar menus, configuração e CSS sem reformular sinais vitais.
**Interfaces:** consome API Task 4, sem timeouts longos: POST rápido e polling. Não colocar caminhos de filesystem ou configurações de ML no fluxo normal da página.

- [x] Preparar cenário de navegador: abrir página, selecionar exercício/vídeo/câmera, iniciar e observar resultado, navegar por repetição, baixar relatório. Incluir API indisponível e repetição não conclusiva.
- [x] Executar cenário antes da página; esperado: página/controles ausentes.
- [x] Implementar seleção, progresso, tabela de repetições, vídeo e canvas de pontos em sincronia; gráfico de medida, comparação oficial separada, erros e download JSON. Limpar polling ao trocar vídeo/sair; impedir resultados antigos de substituírem seleção recente.
- [x] Executar cenário no navegador com API real e também falhas controladas; esperado: fluxo utilizável, sem erros de console, resultado e download corretos. Conferir layout desktop e estreito e navegação da página de sinais vitais.
- [x] Registrar evidência e alterações no ledger; commit local se permitido.

### Task 6: Verificação final e pendências da Fase 4

**Files:** documentação de uso, lock das dependências efetivamente instaladas, resultados agregados e checklist final em `docs/fisioterapia/`.
**Interfaces:** consome resultados reais de todas as tarefas; não altera o escopo sem nova decisão do usuário.

- [x] Rodar suite inteira, sintaxe JS, experimento agrupado e fluxo de navegador; esperado: evidências separadas de engenharia, métricas e limitações. Não repetir extração se hashes permanecerem iguais.
- [x] Comparar implementação com cada critério do desenho e registrar qualquer item ainda pendente ou bloqueado.
- [x] Solicitar revisão independente da alteração completa; corrigir achados importantes com regressão e repetir os checks afetados.
- [x] Documentar instalação Python 3.12, preparação de 2,7 GB, processamento, treino, avaliação, execução da API/frontend e citação/licença. Comandos não devem conter caminhos pessoais.
- [x] Atualizar checklist da Fase 4: áudio/Azure, anomalias temporais/prescrições/movimentação na internação, fusão, alertas, relatório técnico e vídeo final. Distinguir o módulo entregue da validação experimental ainda necessária.
- [x] Registrar evidência final, estado de Git e próximos itens; sem merge, push ou publicação.

## Revisão do próprio plano

Os seis critérios de maior risco têm testes nas Tasks 1–5. Geometria usa pixels/aspect ratio real, teste não recebe rótulo, grupos são de pessoas (não de câmeras), relatórios distinguem predição de referência e a demonstração usa modelos OOF. Métricas e tempo só serão declarados após execução. A autorização do usuário inclui planejar, implementar e testar; execução contínua nesta sessão, sem nova rodada de confirmação do mesmo escopo.
