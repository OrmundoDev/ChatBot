# 3. Estrutura de Pastas e Arquivos

## 3.1 Árvore completa (arquivos relevantes)

```
chatbot-app/
├── .gitignore
├── docker-compose.yml
└── backend/
    ├── .dockerignore
    ├── .env                          # segredos — nunca commitado
    ├── Dockerfile
    ├── alembic.ini
    ├── requirements.txt
    ├── alembic/
    │   ├── env.py
    │   └── versions/
    │       └── 001_initial_clean_schema.py
    ├── knowledge_base/
    │   └── documents/
    │       └── <slug-da-empresa>/    # um TXT/PDF por documento real
    ├── scripts/
    │   ├── ingest_documents.py
    │   └── teste_ia.py
    └── app/
        ├── __init__.py
        ├── main.py                   # ponto de entrada FastAPI
        ├── core/
        │   └── config.py             # variáveis de ambiente centralizadas
        ├── models/
        │   └── chat.py                # schemas Pydantic do endpoint /chat
        ├── api/
        │   ├── dependencies/
        │   │   └── db.py              # injeção da sessão do banco
        │   ├── routes/                # existe, mas vazio — não usado hoje
        │   └── webhooks/
        │       ├── whatsapp_cloud.py
        │       └── evolution.py
        ├── channels/
        │   ├── base.py                 # contrato ChannelProvider
        │   ├── factory.py
        │   └── providers/
        │       ├── whatsapp_cloud_provider.py
        │       ├── evolution_provider.py
        │       ├── telegram_provider.py    # stub
        │       ├── instagram_provider.py   # stub
        │       └── webchat_provider.py     # stub
        ├── llm/
        │   ├── base.py                 # contrato LLMProvider
        │   ├── factory.py
        │   └── providers/
        │       ├── openai_provider.py
        │       └── ollama_provider.py
        ├── db/
        │   ├── base.py                 # Base declarativa do SQLAlchemy
        │   ├── session.py              # engine + fábrica de sessões
        │   ├── models/                 # um arquivo por tabela
        │   └── repositories/           # queries organizadas por tabela
        └── services/
            ├── agent_service.py
            ├── conversation_service.py   # orquestrador principal
            ├── history_service.py
            ├── knowledge_service.py
            ├── embedding_service.py
            ├── chunking_service.py
            ├── prompt_builder.py
            └── ollama_service.py         # legado, pré-multi-tenant
```

## 3.2 Pastas, uma a uma

### `backend/app/core/`
**Finalidade:** configuração central da aplicação. **Quando é usado:** toda
vez que qualquer parte do sistema precisa ler uma variável de ambiente
(chave da API, credenciais do banco). **Quem utiliza:** literalmente todo o
resto do backend, direta ou indiretamente. **Arquivos:** só `config.py`.

### `backend/app/models/`
**Finalidade:** schemas Pydantic que definem o formato de entrada/saída HTTP
(diferente de `db/models/`, que são as tabelas do banco — nomes parecidos,
propósitos diferentes, atenção a essa distinção). **Quando é usado:** na
validação automática do FastAPI. **Quem utiliza:** hoje só o endpoint
`/chat` em `main.py`.

### `backend/app/api/`
**Finalidade:** camada HTTP — rotas e webhooks. **Subpastas:**
`dependencies/` tem funções reutilizáveis injetadas nas rotas (hoje só
`get_db`, que abre e fecha a sessão do banco automaticamente a cada
request); `routes/` existe na estrutura mas está vazia (`__init__.py` sem
conteúdo) — foi criada prevendo uma futura API REST para um painel
administrativo, mas nada foi implementado ali ainda; `webhooks/` tem os dois
endpoints que efetivamente recebem mensagens do mundo real.

### `backend/app/channels/`
**Finalidade:** abstração de canal de mensagem (ver
[capítulo 2, seção 2.5](./02-arquitetura.md)). **Quando é usado:** toda
mensagem recebida ou enviada passa por aqui. **Impacto se alterado:** mudar
`base.py` (o contrato `ChannelProvider`) exige atualizar todos os
providers que o implementam — mudança de alto impacto, mexe em tudo que fala
com WhatsApp/Telegram/etc.

### `backend/app/llm/`
**Finalidade:** abstração de provedor de IA — mesmo padrão do `channels/`,
aplicado ao modelo de linguagem.

### `backend/app/db/`
**Finalidade:** tudo relacionado a persistência. `base.py` só declara a
classe `Base` (propositalmente isolada — ver comentário no próprio arquivo:
importar o engine aqui quebraria o Alembic). `session.py` cria a conexão de
fato. `models/` tem um arquivo por tabela do banco (`company.py`,
`agent.py`, etc.), cada um definindo colunas e relacionamentos via
SQLAlchemy. `repositories/` isola as queries SQL do resto do sistema — os
services nunca escrevem SQL diretamente, sempre chamam um método de um
repository (ex: `ChannelRepository.get_by_identifier(...)`). **Impacto se
alterado:** qualquer mudança em `db/models/` normalmente exige uma nova
migration do Alembic (ver [capítulo 4](./04-banco-de-dados.md)) — model e
banco real precisam ficar sempre sincronizados manualmente neste projeto
(não há `--autogenerate` sendo usado até o momento).

### `backend/app/services/`
**Finalidade:** a lógica de negócio de verdade. É a camada mais importante
para entender o comportamento do chatbot. `conversation_service.py` é o
orquestrador — chama todos os outros services na ordem certa (detalhado no
[capítulo 17](./17-fluxo-completo-mensagem.md)). Os demais têm
responsabilidade única cada um: `agent_service.py` carrega a configuração do
agente do banco; `knowledge_service.py` faz a busca RAG; `history_service.py`
gerencia o histórico de conversa; `embedding_service.py` fala com a OpenAI
para gerar vetores; `chunking_service.py` fatia texto; `prompt_builder.py`
monta a lista final de mensagens enviada à IA. `ollama_service.py` é código
legado de antes da arquitetura multi-tenant — não é mais chamado por nenhum
fluxo ativo, mantido apenas por não ter sido removido ainda.

### `backend/scripts/`
**Finalidade:** scripts que rodam manualmente, fora do ciclo normal de
requisição HTTP. `ingest_documents.py` é o script real de produção (ver
[capítulo 8](./08-processo-de-ingestao.md)). `teste_ia.py` é um script de
teste manual do `ollama_service.py` legado — não reflete o pipeline real de
RAG atual (não faz busca no banco, só simula um contexto fixo).

### `backend/knowledge_base/documents/`
**Finalidade:** onde ficam os arquivos-fonte (PDF/TXT) de cada empresa antes
da ingestão. **Importante:** esta pasta é montada como *bind mount* no
Docker (`./backend/knowledge_base:/app/knowledge_base` no
`docker-compose.yml`) — ou seja, os arquivos aqui existem no disco da VPS,
fora do container, e sobrevivem a rebuilds. Está no `.gitignore` — não vai
para o Git.

### `backend/alembic/`
**Finalidade:** histórico versionado de mudanças no schema do banco. Ver
[capítulo 4](./04-banco-de-dados.md) para o funcionamento completo.

## 3.3 Arquivos de configuração na raiz

| Arquivo | Finalidade | Vai para o Git? |
|---|---|---|
| `docker-compose.yml` | Define os 5 serviços e como se conectam | Sim |
| `.gitignore` | Lista o que nunca deve ser commitado | Sim |
| `backend/Dockerfile` | Receita de como construir a imagem do backend | Sim |
| `backend/.dockerignore` | O que não entra na imagem Docker (mesmo raciocínio do `.gitignore`, mas para o build) | Sim |
| `backend/requirements.txt` | Lista travada de versões de todas as dependências Python | Sim |
| `backend/alembic.ini` | Configuração do Alembic (caminhos, logging) | Sim |
| `backend/.env` | Segredos reais (senhas, chave da OpenAI) | **Não — nunca** |
