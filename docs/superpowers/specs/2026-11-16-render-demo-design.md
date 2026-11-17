# Demonstração gratuita no Render

Objetivo: publicar frontend estático e backend FastAPI gratuito em branch própria, mantendo o sistema local completo. Decisão delegada pelo usuário: modo demonstrativo sintético, isolado por `DEMO_MODE=1`, sem IA paga, dataset de vídeo ou dados cadastrais reais. Todas as telas e respostas indicam a simulação.

Alternativas: execução completa requer vídeos de vários GB e inferência pesada; página puramente estática perde a interação da API. Adotamos API leve determinística com contratos das telas existentes, seis gráficos de sinais e relatórios simulados dos quatro exercícios. Na fisioterapia não haverá reprodução de vídeo; a tela explicará que somente resultados de exemplo estão disponíveis.

Deploy: Python 3.12, Uvicorn um worker, dependências mínimas; Static Site com configuração pública gerada durante build. URL do backend e CORS do frontend por variáveis, timeouts de 120s para cold start. `/health` expõe modo. Nenhuma chave é necessária. Arquivos locais e fluxo sem DEMO_MODE continuam funcionando.
