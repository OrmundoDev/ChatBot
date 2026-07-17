# 11. Backend

## 11.1 Iniciar o backend

Em produção (VPS), o backend sobe como parte do Docker Compose — não se
executa `uvicorn` manualmente fora de container:

```bash
cd ~/chatbot-app
docker compose up -d backend
```

Isso só funciona se `postgres` também estiver rodando (dependência declarada
em `depends_on` no `docker-compose.yml`) — o Compose sobe as dependências
automaticamente se você rodar `docker compose up -d` sem especificar um
serviço.

## 11.2 Parar e reiniciar

```bash
docker compose stop backend      # para sem remover o container
docker compose start backend     # inicia de novo, sem rebuild
docker compose restart backend   # para + inicia (não reconstrói a imagem)
docker compose up -d --build backend  # reconstrói a imagem e reinicia — necessário após editar código
```

## 11.3 Modo desenvolvimento vs. produção

Hoje o projeto **não tem** uma distinção formal de ambiente (não existe
`docker-compose.dev.yml` nem flag de debug separada) — o mesmo Dockerfile e
`docker-compose.yml` rodam em produção diretamente na VPS. O Uvicorn sobe
sem `--reload` (recarregamento automático a cada mudança de arquivo), então
qualquer alteração de código exige rebuild manual (seção 11.2). Se for
necessário um ciclo de desenvolvimento mais rápido no futuro, a forma padrão
seria adicionar `--reload` ao `CMD` do Dockerfile (ou sobrescrever via
`docker-compose.override.yml`) e montar o código como *bind mount* em vez de
`COPY` — mas isso não deve ser feito na configuração de produção, porque
`--reload` tem overhead de performance e reduz estabilidade.

## 11.4 Logs

```bash
docker compose logs backend           # todo o histórico de logs desde que o container subiu
docker compose logs backend -f        # acompanha em tempo real (Ctrl+C para sair)
docker compose logs backend --tail=80 # só as últimas 80 linhas
```

Ver [capítulo 12](./12-logs.md) para como interpretar o conteúdo desses
logs.

## 11.5 Debug — acessar um shell dentro do container

```bash
docker compose exec backend bash
```

De dentro desse shell, é possível rodar Python interativo
(`python3`), inspecionar variáveis de ambiente (`env`), ou rodar scripts
manualmente (`python -m scripts.ingest_documents ...`, capítulo 8).

## 11.6 Migrations — quando e como rodar

Depois de qualquer mudança no schema do banco (nova migration criada), é
necessário aplicá-la:

```bash
docker compose exec backend alembic upgrade head
```

Isso deve rodar **antes** do backend tentar usar uma tabela/coluna nova —
se o código já espera uma coluna que ainda não existe no banco, toda
requisição relacionada vai falhar com erro do SQLAlchemy. Ver
[capítulo 14](./14-deploy.md) para o fluxo completo de deploy incluindo esse
passo.

## 11.7 Monitoramento básico

Não há uma ferramenta de monitoramento dedicada (ex: Grafana, Sentry)
configurada hoje. A forma de saber se o backend está saudável:

```bash
docker compose ps                       # o container está "Up"?
curl http://127.0.0.1:8000/health        # de dentro da VPS
curl https://api.speedbot.space/health   # de fora, validando o Nginx também
```

`/health` (`app/main.py`) devolve `{"status": "healthy", "timestamp": "..."}`
sem tocar no banco — então um `200` nesse endpoint confirma que o processo
Python está de pé, mas não garante que o banco esteja acessível. Para
validar o banco junto, use `/` (endpoint raiz), que também não consulta o
banco hoje, ou uma chamada real ao `/chat`.
