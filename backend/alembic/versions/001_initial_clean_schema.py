"""
Migração 001 — Schema inicial limpo (multi-agente).

O que esta migração faz:
  1. Habilita extensões: uuid-ossp e vector
  2. Cria as 8 tabelas em ordem correta (respeitando FKs)
  3. Cria índices de performance
  4. Insere empresa padrão + agente padrão + canal padrão

Banco vazio — sem migração de dados anteriores.
"""

from alembic import op
from sqlalchemy import text

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

_DEFAULT_SYSTEM_PROMPT = (
    "Você é um assistente virtual que ajuda com diversos assuntos, "
    "com conhecimento especializado em imigração.\n\n"
    "INSTRUÇÕES:\n"
    "1. Quando o CONTEXTO abaixo contiver informação relevante para a "
    "pergunta, use-o como base principal da resposta.\n"
    "2. Quando o CONTEXTO não for relevante para a pergunta, ou estiver "
    "vazio, responda normalmente usando seu próprio conhecimento, como "
    "qualquer assistente de IA faria.\n"
    "3. Nunca mencione a existência de um 'contexto', 'documentos' ou "
    "'base de conhecimento'.\n"
    "4. A resposta deve parecer uma conversa natural e fluida."
)


def upgrade() -> None:
    conn = op.get_bind()
    print("\n  [001] Iniciando criação do schema...")

    # ── Extensões ──────────────────────────────────────────────────────────
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    print("  [001] Extensões habilitadas (uuid-ossp, vector)")

    # ── 1. companies ───────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE companies (
            id         UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
            name       VARCHAR(255) NOT NULL,
            slug       VARCHAR(100) NOT NULL UNIQUE,
            status     VARCHAR(20)  NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """))
    print("  [001] ✅ companies")

    # ── 2. users ───────────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE users (
            id            UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id    UUID         NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            name          VARCHAR(255) NOT NULL,
            email         VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role          VARCHAR(50)  NOT NULL DEFAULT 'operator',
            status        VARCHAR(20)  NOT NULL DEFAULT 'active',
            created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """))
    print("  [001] ✅ users")

    # ── 3. agents ──────────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE agents (
            id            UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id    UUID         NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            name          VARCHAR(255) NOT NULL,
            description   TEXT,
            llm_provider  VARCHAR(50)  NOT NULL DEFAULT 'openai',
            llm_model     VARCHAR(100),
            temperature   FLOAT        NOT NULL DEFAULT 0.4,
            system_prompt TEXT         NOT NULL,
            status        VARCHAR(20)  NOT NULL DEFAULT 'active',
            created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """))
    print("  [001] ✅ agents")

    # ── 4. channels ────────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE channels (
            id         UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
            agent_id   UUID         NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            provider   VARCHAR(50)  NOT NULL,
            identifier VARCHAR(255) NOT NULL,
            name       VARCHAR(255),
            status     VARCHAR(20)  NOT NULL DEFAULT 'active',
            config     JSONB,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """))
    print("  [001] ✅ channels")

    # ── 5. conversations ───────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE conversations (
            id         UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
            agent_id   UUID         NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            channel_id UUID         REFERENCES channels(id) ON DELETE SET NULL,
            session_id VARCHAR(255) NOT NULL,
            from_id    VARCHAR(255),
            status     VARCHAR(30)  NOT NULL DEFAULT 'ai_active',
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """))
    # Índice composto: session_id + agent_id é a busca mais frequente do sistema
    conn.execute(text(
        "CREATE INDEX idx_conversations_session "
        "ON conversations (session_id, agent_id)"
    ))
    print("  [001] ✅ conversations")

    # ── 6. messages ────────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE messages (
            id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
            conversation_id UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role            VARCHAR(20) NOT NULL,
            content         TEXT        NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    # Índice: busca por conversation + ordem cronológica (HistoryService)
    conn.execute(text(
        "CREATE INDEX idx_messages_conversation "
        "ON messages (conversation_id, created_at)"
    ))
    print("  [001] ✅ messages")

    # ── 7. documents ───────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE documents (
            id         UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id UUID         NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            agent_id   UUID         REFERENCES agents(id) ON DELETE SET NULL,
            name       VARCHAR(255) NOT NULL,
            file_path  VARCHAR(500),
            status     VARCHAR(20)  NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """))
    print("  [001] ✅ documents")

    # ── 8. chunks ──────────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE chunks (
            id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
            document_id UUID        REFERENCES documents(id) ON DELETE CASCADE,
            company_id  UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            agent_id    UUID        REFERENCES agents(id) ON DELETE SET NULL,
            content     TEXT        NOT NULL,
            embedding   vector(1536),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    # Índice: busca RAG filtra por company_id antes do cálculo vetorial
    conn.execute(text(
        "CREATE INDEX idx_chunks_company "
        "ON chunks (company_id)"
    ))
    print("  [001] ✅ chunks")

    # ─────────────────────────────────────────────────────────────────────
    # DADOS INICIAIS
    # Empresa + agente + canal padrão para manter o n8n funcionando
    # imediatamente após a migração, sem precisar configurar nada no banco.
    # ─────────────────────────────────────────────────────────────────────
    print("\n  [001] Inserindo dados iniciais...")

    result = conn.execute(text("""
        INSERT INTO companies (name, slug)
        VALUES ('Empresa Padrão', 'default')
        RETURNING id
    """))
    company_id = result.fetchone()[0]
    print(f"  [001] ✅ Empresa padrão: {company_id}")

    result = conn.execute(text("""
        INSERT INTO agents (
            company_id, name, description,
            llm_provider, llm_model, temperature, system_prompt
        ) VALUES (
            :company_id,
            'Assistente de Imigração',
            'Agente padrão — configure pelo painel administrativo (Etapa 6)',
            'openai',
            'gpt-5.4-mini',
            0.4,
            :prompt
        )
        RETURNING id
    """), {"company_id": company_id, "prompt": _DEFAULT_SYSTEM_PROMPT})
    agent_id = result.fetchone()[0]
    print(f"  [001] ✅ Agente padrão: {agent_id}")

    # Canal padrão para compatibilidade com o n8n atual
    # config vazio = usa fallback do .env enquanto não migramos para o banco
    conn.execute(text("""
        INSERT INTO channels (agent_id, provider, identifier, name, config)
        VALUES (:agent_id, 'evolution', 'default', 'Evolution via n8n', '{}')
    """), {"agent_id": agent_id})
    print("  [001] ✅ Canal padrão (evolution/n8n)")

    print("\n  [001] Schema criado com sucesso.\n")


def downgrade() -> None:
    """Remove todas as tabelas em ordem reversa (respeitando FKs)."""
    conn = op.get_bind()
    for table in [
        "chunks", "documents",
        "messages", "conversations",
        "channels", "agents",
        "users", "companies",
    ]:
        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    print("  [001] Downgrade: todas as tabelas removidas")