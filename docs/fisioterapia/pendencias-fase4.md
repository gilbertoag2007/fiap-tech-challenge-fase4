# Conferência da entrega da Fase 4

Fonte: enunciado `IADT - Fase 4 - Tech challenge.pdf`, páginas 3–4, fornecido pelo usuário. Este checklist distingue o módulo de fisioterapia do escopo completo; foi atualizado após a extração integral, avaliação agrupada e testes reais de navegador. As evidências e limitações estão em [resultados.md](resultados.md).

| Item | Estado nesta etapa |
|---|---|
| Vídeos de fisioterapia: quatro exercícios REHAB24-6 | Implementado e testado: 94 vídeos/260.750 frames, quatro exercícios, duas câmeras |
| Detectar execuções fora do padrão | Avaliado com cinco grupos por participante; BA Ex1 64,14%, Ex2 64,59%, Ex3 45,45%, Ex4 73,40%. Ex3 é pendência de qualidade; ver cobertura e recalls no relatório |
| Relatório automático de vídeo | Implementado por repetição, com medidas e limitações; não identifica causa clínica do erro |
| Análise de áudios de consultas e alterações vocais | Pendente |
| Azure Speech to Text | Pendente |
| Azure Text Analytics: termos críticos e sentimentos | Pendente |
| Anomalias em séries temporais de sinais vitais | Parcial: estatísticas e interpretação agregada existem; detector da sequência temporal ainda falta |
| Anomalias na evolução de prescrições | Pendente |
| Anomalias de movimentação durante internação | Pendente; exercícios de fisioterapia não comprovam por si só esse contexto |
| Alertas automáticos para a equipe médica | Pendente |
| Fusão multimodal e monitoramento em tempo real | Pendente |
| Código completo em Git | Código, testes e documentação na branch feature/modal-video; revisão independente concluída; pesos YOLO e modelos treinados incluídos; vídeos e caches não são versionados |
| Relatório técnico multimodal com modelos, resultados e exemplos | Relatório técnico do estado atual em `docs/relatorio-tecnico-fase4.md` e PDF; resultados multimodais ainda dependem dos módulos pendentes |
| Vídeo final até 15 min no YouTube/Vimeo | Ainda não confirmado/produzido nesta etapa |

Não confundir segmentação fornecida pelo dataset com detecção automática de repetições, ou rótulos oficiais com resultados previstos. Também não confundir falha de marcador (`mocap_erroneous`) com exercício incorreto.

## Pontos da base existente a revisar antes da demonstração final

- O importador PhysioNet limita a janela a 600 amostras e atribui datas aleatórias de 2026. Rever a janela conforme a frequência de amostragem e preservar/distinguir as datas reais, antes de demonstrar detecção temporal.
- A IA de sinais vitais recebe estatísticas agregadas, não a sequência temporal completa. Um relatório descritivo não comprova detecção de anomalias ao longo do tempo.
- A importação dos sinais vitais ainda não é acionada pelo frontend. A ampliação do CORS feita para o módulo de vídeo não acrescenta esse botão/fluxo.
- O arquivo de referências dos sinais não estava presente no checkout auditado; revisar sua disponibilização reproduzível.
- A integração real com PhysioNet/OpenAI não foi executada neste módulo; os testes de vídeo não comprovam o funcionamento desses serviços.

## Prioridade após este módulo

1. Melhorar e reavaliar a qualidade do Ex3 e a cobertura da câmera 18 em Ex1/Ex2, preservando uma avaliação independente para novas alegações. Os testes de engenharia aprovados não validam a qualidade clínica.
2. Definir os dados e critérios ainda não especificados para áudio, prescrições, movimentação de internação e alertas; essas escolhas precisam ser esclarecidas com o usuário antes da implementação.
3. Implementar e testar os módulos multimodais restantes e as integrações Azure.
4. Atualizar o relatório técnico com os futuros resultados multimodais e produzir/publicar a demonstração de até 15 minutos solicitada no enunciado.
