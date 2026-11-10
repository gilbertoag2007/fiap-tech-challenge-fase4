# Módulo de vídeo de fisioterapia — desenho para revisão

Data: 10/11/2026. Estado: aprovado pelo usuário; implementação e testes autorizados nesta conversa.

## Objetivo e decisões do usuário

Adicionar ao projeto acadêmico existente a análise dos vídeos do REHAB24-6 para quatro exercícios: Ex1 (abdução do braço direito), Ex2 (braços V–W), Ex3 (flexão com as mãos apoiadas na mesa) e Ex4 (abdução de perna). Usar YOLOv8 Pose para extrair a postura e um classificador de movimentos treinado com os rótulos do dataset. Implementar e testar este módulo primeiro; depois reavaliar as pendências da entrega completa da Fase 4.

O escopo acordado é o dataset existente, sem entrada de novos vídeos externos. Não relacionar os voluntários do REHAB24-6 aos pacientes do PhysioNet: são fontes e pessoas diferentes.

## Contexto verificado

- Backend em `analise-medica-api`: FastAPI, controlador, serviço e integrações; persistência local de JSON/CSV. Frontend estático em `analise-medica-frontend`: HTML, Bootstrap, JavaScript, Axios e Chart.js.
- A API atual monta apenas as rotas de sinais vitais. O cliente HTTP tem timeout de dez segundos e o CORS permite apenas GET; o novo fluxo precisa de criação de análise por POST e consulta de progresso por GET.
- Não há processamento de vídeo, suite automatizada de testes ou configuração de ambiente Python do projeto. O host é macOS arm64; há um runtime Python 3.12 disponibilizado pelo ambiente. Não assumir compatibilidade das bibliotecas de visão com o Python 3.14 do sistema.
- O REHAB24-6 oferece vídeos RGB de duas câmeras, intervalos de repetições a 30 FPS e rótulo binário por repetição. Os esqueletos oficiais são dados de captura de movimento, não estimativas produzidas pelo YOLO.
- O enunciado pede processamento de vídeo, detecção de movimentos anômalos e relatórios; OpenPose e YOLOv8 aparecem como exemplos. Este módulo atende à parte de fisioterapia, não à entrega multimodal inteira.

## Abordagens consideradas e escolha

1. Estimador de postura com regras de ângulo e alinhamento: fácil de explicar, mas exige limites fundamentados para cada exercício e erro. Não escolhido como classificador principal.
2. Estimador de postura com classificador supervisionado por exercício: usa os rótulos existentes e permite avaliação empírica em participantes não vistos. É a abordagem escolhida na proposta aceita.

A primeira proposta citava MediaPipe. O usuário escolheu YOLOv8 Pose após conferir as tecnologias sugeridas no PDF. Não é necessário acrescentar OpenPose para esta versão.

## Escopo funcional

### Preparação local reproduzível

- Um comando de preparação baixa `videos.zip`, `Segmentation.csv` e `Segmentation.txt` da versão `13305826`, valida os checksums publicados e extrai com proteção contra caminhos fora do diretório de destino. O pacote de vídeos completo tem cerca de 2,7 GB; apenas Ex1–Ex4 entram no catálogo e nos experimentos. Download interrompido não deve parecer um arquivo válido.
- Um manifesto local registra origem, checksum, exercício, participante do dataset, câmera, FPS, dimensões, total de frames e caminho relativo. Fazer a associação pelo conteúdo e pelos nomes verificados dos arquivos; associação ambígua deve produzir erro explicável.
- Preservar os valores de frames originais. O importador documenta e verifica sua conversão para índices internos e tempos de reprodução, inclusive o tratamento das bordas. A origem dos índices deve ser conferida com amostras reais antes de estabelecer o contrato e seus testes.
- Rejeitar FPS ou intervalos incompatíveis com as anotações em vez de deslocar os rótulos silenciosamente. Não usar dados de 120 FPS com índices de 30 FPS.
- Guardar vídeos, pesos, caches, modelos treinados e resultados em `analise-medica-api/data/fisioterapia/`, ignorados pelo Git. Versionar scripts, manifestos de configuração, dependências e evidências agregadas sem vídeos. Documentar licença acadêmica e citação dos autores.

### Extração da postura

- Usar pesos oficiais `yolov8n-pose.pt`, sem atualizar automaticamente para outra família YOLO. Registrar hash dos pesos, versão de bibliotecas e parâmetros em cada experimento.
- Executar primeiro em CPU para ter caminho portátil; aceleração disponível no host é uma otimização, não requisito funcional. Compatibilidade e tempo de execução serão medidos com vídeo real antes do processamento completo.
- Ler frames sequencialmente sem manter o vídeo inteiro na memória. Cachear coordenadas dos 17 pontos COCO, confiança, pessoa acompanhada e timestamp por frame, com chave dependente do hash do vídeo, pesos e configuração.
- Seguir o participante principal pela continuidade espacial e qualidade dos pontos. Seleção ambígua, oclusão ou mudança de pessoa não pode resultar em classificação confiante; marcar os frames como inválidos e tornar a limitação visível.
- Os esqueletos oficiais não substituem a extração do vídeo. Podem ser usados futuramente para estudar erros da pose, mas não são entrada desta versão.

### Repetições e medidas

- Usar os intervalos oficiais para localizar as repetições. Não prometer descoberta automática das repetições ou reconhecimento automático do exercício nesta versão.
- O catálogo fornece o exercício. Os frames do vídeo fornecem as medidas de movimento. O rótulo `correctness` não é entrada do extrator ou do preditor; fica separado para treinamento e comparação dos resultados.
- Extrair medidas normalizadas por tamanho corporal e ângulos 2D ao longo da repetição: braço/tronco e cotovelo direito em Ex1; ombros e cotovelos bilaterais e simetria em Ex2; cotovelos, ombros/quadris/tornozelos e alinhamento do tronco em Ex3; quadris, joelhos, separação das pernas e inclinação do tronco em Ex4. Não interpretar medidas projetadas em 2D como ângulos anatômicos 3D.
- Descrever cada repetição por estatísticas temporais das medidas (amplitude, quantis, variabilidade e variação entre frames), mantendo ordem temporal nos cálculos. Não usar identificador da pessoa, arquivo, número da repetição, frame absoluto, câmera ou rótulos como variáveis preditoras.
- Proposta técnica: confiança mínima de ponto de 0,5 e cobertura mínima de 60% dos frames para as medidas essenciais. Não interpolar trechos longos nem fabricar postura. Aplicar essas mesmas condições no treino, avaliação e interface; registrar cobertura e motivo de rejeição.
- Dados insuficientes ou associação de pessoa ambígua produzem `Não conclusivo`, não `Correto` por padrão.

### Treinamento e avaliação sem vazamento

- Proposta técnica: Random Forest por exercício, com seed fixa, tratamento de classes desequilibradas e parâmetros registrados. O plano detalhará o esquema exato de features e parâmetros, sem ajustar o modelo aos resultados finais.
- Separar por participante, mantendo todas as repetições e ambas as câmeras da mesma pessoa no mesmo grupo. Nunca dividir frames ou repetições aleatoriamente entre treino e teste.
- Usar validação cruzada em cinco grupos de participantes, com atribuição determinística. Se a distribuição real não permitir cinco grupos com as classes necessárias no treino, o processo deve explicar o impedimento em vez de treinar um modelo inválido.
- Ajustar qualquer transformação ou preenchimento exclusivamente no subconjunto de treino. Não usar informações de repetições futuras ou de outros participantes para preencher a entrada de teste.
- Na demonstração dos vídeos do próprio dataset, usar o modelo do grupo que excluiu aquele participante do treinamento. Guardar os modelos e o manifesto de grupos para reproduzir essas análises.
- Informar precisão, recall da classe incorreta, F1 macro, balanced accuracy, matriz de confusão, cobertura e contagens por exercício e participante. Separar os resultados não conclusivos dos casos classificados e informar ambas as quantidades.
- Comparar com um baseline de classe majoritária, treinado nos mesmos grupos e avaliado nas mesmas repetições. Também apresentar desempenho por câmera como diagnóstico, sem mudar o agrupamento por pessoa.
- Não prometer uma acurácia antes do experimento. O resultado deve permitir verificar se cada exercício supera o baseline; desempenho insuficiente será uma pendência explícita de qualidade, não um teste ocultado ou uma alegação de sucesso.

### API e execução

- Nova área `/v1/fisioterapia`, separada das rotas de sinais vitais. Catalogar exercícios e vídeos preparados; servir apenas vídeos registrados por identificador opaco, sem aceitar caminhos ou URLs fornecidos pelo cliente.
- Criar análise por POST com identificador de vídeo. Responder rapidamente com identificador de tarefa; consultar estado, progresso e resultado por GET. Servir o vídeo com suporte a busca temporal no navegador e disponibilizar relatório JSON para download.
- Proposta técnica para execução acadêmica local: um processo Uvicorn e um executor com um trabalho de vídeo por vez. Persistir metadados e resultados em JSON com escrita atômica; manter o trabalho de visão fora da thread de atendimento HTTP. Não exigir Redis, Celery ou banco nesta versão.
- Estados: `pendente`, `processando`, `concluido`, `falhou`. Persistir falhas com mensagem útil. Ao reiniciar, marcar trabalhos interrompidos como falhos e permitir nova tentativa; não fingir que há recuperação automática.
- Requisições repetidas para o mesmo vídeo e versão de modelo reutilizam trabalho ativo ou resultado concluído. Alterações de vídeo, configuração ou modelo invalidam o cache.
- Preparação de dados e treinamento são comandos locais explícitos; não acontecem no primeiro acesso à página. Ausência de dataset, pesos ou classificador gera erro de configuração visível e instruções para preparar o ambiente.
- Ampliar CORS somente para os métodos e cabeçalhos usados pelo frontend local; manter o comportamento atual de sinais vitais.

### Interface e relatório

- Nova página de Fisioterapia no mesmo frontend, com acesso pelo menu existente. Selecionar exercício, vídeo e câmera disponíveis no catálogo e iniciar a análise.
- Mostrar progresso, erros recuperáveis, vídeo, pontos corporais sincronizados, gráfico das medidas selecionadas e tabela de repetições. Clicar em uma repetição leva o vídeo ao intervalo correspondente.
- Exibir `Correto`, `Incorreto` ou `Não conclusivo`, cobertura da pose, medidas observadas e intervalo temporal. Disponibilizar o rótulo oficial e a concordância em uma área claramente identificada como avaliação do dataset, separada da predição.
- Relatório determinístico com resumo de repetições, trechos sinalizados, medidas, limitações, versões e indicação de que os intervalos são fornecidos pelo dataset. Esta versão não depende de chamadas pagas a ChatGPT ou Azure para gerar texto.
- Não apresentar score do classificador como probabilidade clínica calibrada. Não inventar causa, gravidade, diagnóstico ou correção terapêutica: os rótulos disponíveis são binários, sem descrição do erro.
- Participante identificado como voluntário do dataset; nenhuma associação com CPF, prontuário ou paciente do catálogo de sinais vitais.

## Critérios de conclusão e testes

1. Ambiente Python compatível e dependências reproduzíveis; API atual continua funcionando no que os testes locais conseguirem verificar, sem chamadas pagas.
2. Testes unitários das medidas e bordas: coordenadas degeneradas, pontos ausentes, baixa confiança, normalização, enquadramento e ausência de pessoa. Testes do importador: CSV inválido, arquivos ausentes, caminhos perigosos, frames fora do vídeo e câmera incorreta.
3. Testes que comprovem ausência de participantes compartilhados entre treino e teste e que a predição funcione sem acesso a `correctness`. Ambas as câmeras de uma pessoa permanecem juntas.
4. Testes de API para catálogo, vídeo, validação, criação/consulta de tarefa, cache, falha, reinício e relatório. Casos rápidos usam doubles do estimador; esses testes não substituem execução real do YOLO.
5. Execução real do YOLO em pelo menos um vídeo de cada exercício, com verificação visual do participante acompanhado, pontos e alinhamento dos intervalos.
6. Experimento completo sobre os vídeos disponíveis de Ex1–Ex4 nas duas câmeras, com métricas e cobertura geradas por participante excluído do treinamento; relatar duração e falhas. Não afirmar qualidade do classificador a partir dos testes sintéticos.
7. Teste de navegador do fluxo selecionar → processar → acompanhar → assistir → navegar por repetição → baixar relatório, incluindo erro de API e estado não conclusivo.
8. Documentação dos comandos de preparação, extração, treinamento, avaliação e execução; resultados medidos e limitações. Nenhuma dependência silenciosa de caminhos pessoais do desenvolvedor.

Conclusão de engenharia e qualidade experimental são registradas separadamente. Caso a classificação não supere o baseline em algum exercício, isso impede declarar aquele exercício validado; investigar melhorias apenas nos grupos de desenvolvimento e reservar avaliação independente para novas alegações.

## Fora deste módulo

Novos vídeos externos, webcam, streaming ao vivo, identificação automática de exercícios, segmentação automática de repetições, aplicações em cirurgias, prescrição de exercícios, áudio, integração Azure, evolução de prescrições, fusão multimodal e notificação à equipe médica. Esses itens serão reavaliados frente ao enunciado após esta implementação e seus testes.

## Decisões técnicas propostas para revisão

O usuário escolheu os quatro exercícios, o dataset e YOLOv8 Pose. As decisões de implementação propostas neste documento são: execução local, catálogo sem upload externo, intervalos oficiais, modelo `yolov8n-pose.pt`, Random Forest por exercício, avaliação por cinco grupos de participantes, demonstração com participante excluído do treino, relatório sem LLM, executor local de um trabalho e interface integrada ao frontend existente. Ajustes de parâmetros de engenharia deverão ser registrados com justificativa e não poderão ser apresentados como requisitos clínicos.

## Fontes

- Dataset, arquivos, licença e citação: https://zenodo.org/records/13305826
- Dicionário das anotações: https://zenodo.org/records/13305826/files/Segmentation.txt?download=1
- Variantes oficiais de YOLOv8: https://docs.ultralytics.com/models/yolov8/
- Extração de pontos corporais: https://docs.ultralytics.com/tasks/pose/
- Enunciado lido: `IADT - Fase 4 - Tech challenge.pdf`, páginas 3–4, fornecido pelo usuário.

## Esclarecimentos encontrados na implementação

- A conferência do ZIP completo confirmou 94 vídeos Ex1–Ex4 (26, 24, 20 e 24 respectivamente), 260.750 frames e 703 repetições únicas anotadas, vistas por duas câmeras. As métricas por câmera contam até 1.406 observações, não 1.406 repetições independentes.
- As anotações alcançam `first_frame=1`; em PM_045 e PM_103, nas duas câmeras, `last_frame` coincide com o total de frames. O adaptador preserva os números oficiais e usa conversão compatível com origem 1/final inclusivo para índices internos de origem 0. Essa evidência é registrada no catálogo, pois o dicionário textual não explicita a origem.
- Após mais de 15 frames sem associação, o rastreamento perde a identidade e não a retoma por simples sobreposição espacial. A perda deve reduzir cobertura/produzir resultado não conclusivo, sem assumir reidentificação.
- A divisão de grupos inclui participantes mesmo quando suas repetições não têm pose utilizável. Apenas as amostras efetivamente ajustadas pelo classificador são filtradas por qualidade.
- Compartilhar identidade da engine (Ultralytics/PyTorch/OpenCV/política de rastreamento) entre extração e treinamento; validar também o arquivo de pose antes de reutilizar um relatório.
