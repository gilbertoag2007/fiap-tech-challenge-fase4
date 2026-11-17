# Demonstração no Render gratuito

Branch: `codex/render-free-demo`. A execução local normal continua igual, sem `DEMO_MODE`.

A demonstração usa dois pacientes fictícios, curvas matemáticas dos seis sinais e três repetições simuladas por exercício. Nenhum dado clínico, chamada OpenAI, download PhysioNet, vídeo REHAB24-6 ou inferência YOLO é utilizado. A tela de fisioterapia mostra resultados e gráficos ilustrativos; não reproduz vídeo. Não é uma demonstração da precisão dos modelos.

## Backend — Web Service, Free

- Repositório: `gilbertoag2007/fiap-tech-challenge-fase4`
- Branch: `codex/render-free-demo`
- Root Directory: `analise-medica-api`
- Runtime: Python
- Build: `pip install -r requirements-render.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
- Health check: `/health`
- Variáveis: `PYTHON_VERSION=3.12.8`, `DEMO_MODE=1`, `FRONTEND_ORIGINS=https://URL-DO-FRONTEND.onrender.com`

Não configure chave OpenAI, disco persistente ou serviços pagos. A API demo não grava estado. `/health` deve retornar `{"status":"ok","mode":"demo"}`. Os dados sintéticos retornam iguais após reinicializações.

## Frontend — Static Site

- Mesmo repositório e branch; Root Directory vazio.
- Build: `python3 scripts/build-render-frontend.py`
- Publish directory: `dist/frontend`
- Variáveis: `API_BASE_URL=https://URL-DO-BACKEND.onrender.com`, `DEMO_MODE=1`.

O build gera somente configuração pública, nunca segredos. Depois de conhecer a URL estática, atualize `FRONTEND_ORIGINS` no backend. Aceita múltiplas origens separadas por vírgula. As origens locais continuam permitidas.

`render.yaml` permite provisionar a mesma estrutura por Blueprint; informe as duas URLs quando solicitado. Use apenas uma modalidade para evitar criar serviços duplicados.

## Verificação

1. Abra `/health` e confirme `mode=demo`.
2. Na tela Sinais Vitais selecione qualquer paciente; confira seis gráficos e o aviso sintético.
3. Em Fisioterapia escolha um dos quatro exercícios e clique em “Explorar resultado simulado”; confira as três repetições e baixe o JSON com `demo=true`.
4. Confira o banner nas três páginas. Não há reprodução real de vídeo nesta versão.

O backend gratuito pode suspender após inatividade; a primeira consulta tem timeout de 120 segundos. O frontend estático permanece disponível durante a inicialização. Disponibilidade depende das cotas gratuitas da conta Render.

## Ensaio local do build

```sh
API_BASE_URL=https://sua-api.onrender.com DEMO_MODE=1 python3 scripts/build-render-frontend.py
DEMO_MODE=1 analise-medica-api/.venv/bin/python -m uvicorn main:app --app-dir analise-medica-api --port 8000
```

Para ensaio local completo, use URL local diretamente no `APP_CONFIG` de uma cópia temporária; o build de produção rejeita origens HTTP.
