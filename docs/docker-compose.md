# Docker Compose no WSL

Na raiz, com Docker disponível:

```sh
docker compose up -d --build
```

Frontend: http://localhost:5500. Swagger: http://localhost:8000/docs.
Nginx serve os arquivos e encaminha /v1/ para o backend na rede Docker.
O navegador usa a mesma origem. As portas ficam restritas ao host.
A execução sem Docker permanece com a configuração original.

O backend inclui vídeo em CPU e um worker para preservar a fila local.
O primeiro build baixa dependências grandes do PyTorch. O serviço dataset-init
executa a preparação do dataset antes do backend iniciar. O frontend aguarda o
backend ficar saudável. Não há treino automático.

Na primeira execução, a preparação baixa aproximadamente 2,5 GB e extrai os
vídeos. Nas seguintes, verifica e reutiliza os downloads existentes. A preparação
ainda consulta o Zenodo para obter metadados e conferir checksums. Se falhar,
o backend não inicia; consulte os logs, corrija a causa e execute up novamente.
O dataset-init terminar em Exited (0) é esperado: é uma tarefa, não um servidor.

Para acompanhar em outro terminal:

```sh
docker compose logs -f dataset-init
docker compose ps -a
```

O prepare não informa percentual de download. Para observar os arquivos:

```sh
watch -n 5 'du -sh analise-medica-api/data/fisioterapia/downloads analise-medica-api/data/fisioterapia/videos 2>/dev/null'
```

Não execute outra preparação simultaneamente na mesma pasta.

## Persistência e credenciais

A pasta analise-medica-api/data é montada em /app/data. Catálogos, vídeos,
modelos, relatórios e caches existentes são reaproveitados e persistem após
remover containers. Os pesos e classificadores versionados devem estar presentes.
Dados e credenciais não são copiados para as imagens.

O Compose lê opcionalmente .env. A chave OpenAI é necessária
somente para importar/analisar sinais, não para iniciar os serviços ou usar vídeo.
Recrie o backend após mudar esse arquivo: docker compose up -d --force-recreate backend.

Para configurar, copie `.env.example` para `.env` na raiz do repositório.
Na instalação manual, a API encontra esse mesmo arquivo pelo caminho do código,
independentemente da pasta de execução. Variáveis já definidas no ambiente têm
prioridade sobre o arquivo. No Docker, o Compose injeta os valores no backend;
não é necessário montar ou copiar o arquivo para dentro da imagem.
Se usava `analise-medica-api/.env`, transfira seus valores para o `.env` da raiz:
o caminho antigo deixou de ser lido. Não há migração automática de credenciais.

A preparação é automática. Para conferir os modelos após a inicialização:

```sh
docker compose exec backend python -m fisioterapia evaluate
```

prepare baixa aproximadamente 2,5 GB. evaluate apenas confere compatibilidade e
mostra métricas existentes. Não é preciso treinar novamente.
Se existir data/fisioterapia/runtime.json de outro ambiente, confira o dispositivo:
MPS não funciona no container Linux; use cpu. Caches de outro runtime podem ser
regenerados pelo sistema. Bibliotecas CDN e integrações externas exigem internet.

## Operação

```sh
docker compose ps
docker compose logs -f dataset-init backend frontend
docker compose down
```

Para evitar conflito com serviços locais:

```sh
FRONTEND_PORT=5501 API_PORT=8001 docker compose up -d --build
```

Os healthchecks verificam disponibilidade HTTP, não dataset, credenciais ou
qualidade do modelo. A instalação manual e a alternativa Docker também estão descritas no README raiz.
