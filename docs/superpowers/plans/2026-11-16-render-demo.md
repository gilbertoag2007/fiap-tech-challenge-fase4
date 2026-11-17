# Render free demo Implementation Plan

> Execução pelo subagente de preparação já solicitado pelo usuário, usando executing-plans.

**Goal:** publicar demonstração leve de sinais e fisioterapia.
**Architecture:** app demonstrativa isolada, frontend estático com configuração pública no build.
**Tech Stack:** FastAPI, Python 3.12, HTML/JS.
**Spec:** docs/superpowers/specs/2026-11-16-render-demo-design.md

## Global Constraints
Sem serviços pagos, segredos ou dados pessoais; demonstração explicitamente sintética. Sem alterar execução local completa.

## Review Focus
Identificador inexistente retorna 404; ausência de identificador retorna 422; CORS restrito; não importar bibliotecas pesadas em demo; resultados de fisioterapia nunca apresentados como inferência real.

## Task 1: API leve
- [x] Escrever e executar testes falhos de health, pacientes sintéticos, CSV, relatório, exercícios e erros.
- [x] Implementar demo_app.py e seleção condicional em main.py, requirements-render.txt.
- [x] Executar testes novos e suite Python.

## Task 2: Frontend e deploy
- [x] Escrever testes do build/configuração e indicadores demo.
- [x] Implementar configuração pública, banner, adaptação de fisioterapia sem vídeo e cold start.
- [x] Criar blueprint gratuito e documentação; verificar build e testes de navegador.
- [x] Revisar diff, commit e push da branch para o agente de deploy.
