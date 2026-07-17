# 9. Docker e Docker Compose

## 9.1 Conceitos de base

**Docker** é uma ferramenta que empacota uma aplicação junto com tudo que
ela precisa para rodar (linguagem, bibliotecas, arquivos) num pacote
isolado chamado **container**. **Imagem** é o "molde" — uma receita
imutável construída a partir de um `Dockerfile`. **Container** é uma
instância em execução dessa imagem — você pode rodar vários containers a
partir da mesma imagem. **Volume** é um espaço em disco gerenciado pelo
Docker que sobrevive mesmo se o container for apagado (usado aqui para os
dados do Postgres, por exemplo — sem isso, apagar o container apagaria o
banco inteiro). **Network** é a rede virtual que permite containers se
comunicarem entre si pelo **nome do serviço** em vez de IP (ex: o backend se
conecta ao banco usando o hostname `postgres`, não um IP fixo — isso
funciona porque o Docker Compose cria automaticamente essa rede interna e
registra cada serviço com seu nome).

## 9.2 Dockerfile do backend

```dockerfile
FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Explicando cada instrução: `FROM python:3.10-slim` parte de uma imagem
oficial do Python já pronta, na versão "slim" (mínima, sem ferramentas
desnecessárias, para manter a imagem final menor). `WORKDIR /app` define a
pasta de trabalho dentro do container. `build-essential` é instalado porque
algumas bibliotecas Python (dependências de baixo nível) precisam compilar
código C durante a instalação. `COPY requirements.txt .` seguido de
`RUN pip install` **antes** de `COPY . .` é uma otimização de cache do
Docker: se só o código-fonte mudar (não as dependências), o Docker reutiliza
a camada já construída da instalação de pacotes, tornando rebuilds mais
rápidos. `EXPOSE 8000` documenta a porta usada (não abre a porta sozinho —
isso é feito no `docker-compose.yml`). `CMD` é o comando executado quando o
container inicia: sobe o servidor Uvicorn (servidor ASGI que roda
aplicações FastAPI).

**Ponto crítico para entender:** `COPY . .` copia o código para dentro da
imagem **no momento do build**. Isso significa que editar um arquivo no
disco da VPS **não afeta** um container que já está rodando — é necessário
reconstruir a imagem (`docker compose up -d --build backend`) para que a
mudança tenha efeito. Esse é um erro comum: editar código, reiniciar o
container (`docker compose restart`) e não entender por que a mudança não
apareceu — reiniciar não reconstrói a imagem.

## 9.3 docker-compose.yml — os 5 serviços

```yaml
services:
  postgres:      # banco de dados principal (+ pgvector)
  redis:         # cache, usado pela Evolution API
  evolution_api: # canal de WhatsApp não-oficial (implementado, não usado em produção)
  n8n:           # automação visual (legado, fora do fluxo de produção)
  backend:       # a aplicação FastAPI
```

Pontos importantes de cada serviço:

**`postgres`**: usa a imagem `pgvector/pgvector:pg16` (Postgres 16 já com a
extensão `pgvector` pré-instalada, em vez da imagem oficial genérica).
Exposto só em `127.0.0.1:5432` — inacessível de fora da VPS. Dados
persistidos no volume `postgres_data`.

**`backend`**: `build: context: ./backend` — ao contrário dos outros
serviços (que usam imagens prontas), este é construído a partir do
`Dockerfile` local. `env_file: .env` carrega as variáveis do arquivo `.env`
automaticamente. A linha `environment: EVOLUTION_API_URL: http://evolution_api:8080`
sobrescreve essa variável específica do `.env` — isso é necessário porque,
de dentro de um container, `localhost` significa "este próprio container",
não a máquina host nem outro container. Para o backend alcançar a Evolution
API (que roda em outro container), ele precisa usar o **nome do serviço**
(`evolution_api`), não `127.0.0.1`.

**Nota histórica:** esse bloco `environment:` já teve também uma linha
`POSTGRES_HOST: postgres`, de quando o banco rodava no container `postgres`
deste mesmo `docker-compose.yml`. Ela foi **removida** na migração para o
Supabase — hoje `POSTGRES_HOST` (e as demais variáveis de conexão com o
banco) vêm só do `.env`, apontando pro Supabase. Se essa linha voltar por
engano (num merge ou copy-paste futuro), o backend volta a tentar se
conectar no Postgres local, ignorando o `.env` silenciosamente.

O volume
`./backend/knowledge_base:/app/knowledge_base` é um *bind mount* — conecta
diretamente uma pasta do disco da VPS a uma pasta dentro do container, ao
vivo (mudanças em um lado aparecem no outro imediatamente, sem rebuild —
diferente do código-fonte, que é copiado só no build).

## 9.4 Comandos essenciais

| Comando | O que faz |
|---|---|
| `docker compose up -d` | Sobe todos os serviços em segundo plano (`-d` = detached) |
| `docker compose up -d --build backend` | Reconstrói a imagem do backend e sobe de novo — **use sempre depois de editar código** |
| `docker compose down` | Para e remove todos os containers (mantém os volumes/dados) |
| `docker compose restart backend` | Reinicia o container sem reconstruir a imagem — **não aplica mudanças de código** |
| `docker compose logs backend -f` | Mostra os logs em tempo real (`-f` = follow, continua acompanhando) |
| `docker compose ps` | Lista os containers e seus status |
| `docker compose exec backend bash` | Abre um terminal interativo dentro do container do backend |
| `docker compose exec backend python -m scripts.ingest_documents ...` | Roda um script Python dentro do container (capítulo 8) |
| `docker volume ls` | Lista os volumes existentes |
| `docker system prune` | Remove imagens, containers parados e caches não utilizados — libera espaço em disco |

## 9.5 Atualizar o projeto na VPS (fluxo típico)

```bash
cd ~/chatbot-app
git pull origin main
docker compose up -d --build backend
docker compose logs backend -f    # confirma que subiu sem erro
```

Ver o [capítulo 14 (Deploy)](./14-deploy.md) para o processo completo,
incluindo quando rodar migrations do Alembic.

## 9.6 Limpar o ambiente (cuidado)

`docker compose down -v` remove também os **volumes** — isso apaga
permanentemente os dados do Postgres. Só use isso intencionalmente, nunca
como comando de rotina. Para apenas liberar espaço em disco sem risco a
dados em uso, prefira `docker system prune` (remove só o que está órfão/não
utilizado).
