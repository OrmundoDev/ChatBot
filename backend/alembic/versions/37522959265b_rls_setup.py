"""rls_setup

Revision ID: 37522959265b
Revises: 001
Create Date: 2026-07-17 03:51:33.201031

Migração 002 — RLS (Row Level Security) para o painel administrativo.

O QUE ESTA MIGRAÇÃO FAZ:
  1. Adiciona company_id em messages, conversations e channels
     (denormalizado, mesmo padrão já usado em chunks — evita JOINs
     nas políticas de RLS, que rodam a cada leitura do painel)
  2. Preenche essas colunas nos registros já existentes
  3. Adiciona FK e índice de performance nessas colunas novas
  4. Habilita RLS em todas as 8 tabelas de negócio
  5. Cria as políticas de SELECT/UPDATE necessárias para o painel
  6. Habilita Realtime nas tabelas conversations e messages

IMPORTANTE: o backend continua funcionando sem nenhuma mudança — ele
se conecta como o papel "postgres", que ignora RLS por padrão
(BYPASSRLS). RLS só afeta quem se conecta via API/SDK do Supabase
usando os papéis "anon" ou "authenticated" (ou seja, o painel).
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '37522959265b'
down_revision: Union[str, Sequence[str], None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    print("\n  [002] Iniciando setup de RLS...")

    # ── 1. Colunas novas ─────────────────────────────────────────────────
    conn.execute(text("ALTER TABLE conversations ADD COLUMN company_id UUID"))
    conn.execute(text("ALTER TABLE messages ADD COLUMN company_id UUID"))
    conn.execute(text("ALTER TABLE channels ADD COLUMN company_id UUID"))
    print("  [002] OK - Colunas company_id criadas")

    # ── 2. Preencher dados existentes, usando os relacionamentos atuais ──
    conn.execute(text("""
        UPDATE channels c SET company_id = a.company_id
        FROM agents a WHERE c.agent_id = a.id
    """))
    conn.execute(text("""
        UPDATE conversations conv SET company_id = a.company_id
        FROM agents a WHERE conv.agent_id = a.id
    """))
    conn.execute(text("""
        UPDATE messages m SET company_id = conv.company_id
        FROM conversations conv WHERE m.conversation_id = conv.id
    """))
    print("  [002] OK - Dados existentes preenchidos")

    # ── 3. Tornar obrigatório, FK e índice ────────────────────────────────
    conn.execute(text("ALTER TABLE channels ALTER COLUMN company_id SET NOT NULL"))
    conn.execute(text("ALTER TABLE conversations ALTER COLUMN company_id SET NOT NULL"))
    conn.execute(text("ALTER TABLE messages ALTER COLUMN company_id SET NOT NULL"))

    conn.execute(text("ALTER TABLE channels ADD CONSTRAINT channels_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE"))
    conn.execute(text("ALTER TABLE conversations ADD CONSTRAINT conversations_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE"))
    conn.execute(text("ALTER TABLE messages ADD CONSTRAINT messages_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE"))

    conn.execute(text("CREATE INDEX idx_channels_company ON channels (company_id)"))
    conn.execute(text("CREATE INDEX idx_conversations_company ON conversations (company_id)"))
    conn.execute(text("CREATE INDEX idx_messages_company ON messages (company_id)"))
    print("  [002] OK - Constraints e indices criados")

    # ── 4. Habilitar RLS em todas as tabelas de negócio ──────────────────
    for tabela in ["companies", "users", "agents", "channels", "conversations", "messages", "documents", "chunks"]:
        conn.execute(text(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY"))
    print("  [002] OK - RLS habilitado em todas as tabelas")

    # ── 5. Políticas ───────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE POLICY select_own_company ON companies FOR SELECT
        USING (id = (auth.jwt() -> 'app_metadata' ->> 'company_id')::uuid)
    """))
    conn.execute(text("""
        CREATE POLICY select_own_agents ON agents FOR SELECT
        USING (company_id = (auth.jwt() -> 'app_metadata' ->> 'company_id')::uuid)
    """))
    conn.execute(text("""
        CREATE POLICY select_own_channels ON channels FOR SELECT
        USING (company_id = (auth.jwt() -> 'app_metadata' ->> 'company_id')::uuid)
    """))
    conn.execute(text("""
        CREATE POLICY select_own_conversations ON conversations FOR SELECT
        USING (company_id = (auth.jwt() -> 'app_metadata' ->> 'company_id')::uuid)
    """))
    conn.execute(text("""
        CREATE POLICY update_own_conversations ON conversations FOR UPDATE
        USING (company_id = (auth.jwt() -> 'app_metadata' ->> 'company_id')::uuid)
        WITH CHECK (company_id = (auth.jwt() -> 'app_metadata' ->> 'company_id')::uuid)
    """))
    conn.execute(text("""
        CREATE POLICY select_own_messages ON messages FOR SELECT
        USING (company_id = (auth.jwt() -> 'app_metadata' ->> 'company_id')::uuid)
    """))
    print("  [002] OK - Politicas criadas")
    print("  [002] INFO - users, documents e chunks: RLS ligado, sem politica - bloqueadas por enquanto")

    # ── 6. Realtime nas tabelas que o painel vai escutar ──────────────────
    conn.execute(text("ALTER PUBLICATION supabase_realtime ADD TABLE conversations"))
    conn.execute(text("ALTER PUBLICATION supabase_realtime ADD TABLE messages"))
    print("  [002] OK - Realtime habilitado em conversations e messages")

    print("\n  [002] RLS configurado com sucesso.\n")


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(text("ALTER PUBLICATION supabase_realtime DROP TABLE conversations"))
    conn.execute(text("ALTER PUBLICATION supabase_realtime DROP TABLE messages"))

    conn.execute(text("DROP POLICY IF EXISTS select_own_company ON companies"))
    conn.execute(text("DROP POLICY IF EXISTS select_own_agents ON agents"))
    conn.execute(text("DROP POLICY IF EXISTS select_own_channels ON channels"))
    conn.execute(text("DROP POLICY IF EXISTS select_own_conversations ON conversations"))
    conn.execute(text("DROP POLICY IF EXISTS update_own_conversations ON conversations"))
    conn.execute(text("DROP POLICY IF EXISTS select_own_messages ON messages"))

    for tabela in ["companies", "users", "agents", "channels", "conversations", "messages", "documents", "chunks"]:
        conn.execute(text(f"ALTER TABLE {tabela} DISABLE ROW LEVEL SECURITY"))

    conn.execute(text("ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_company_id_fkey"))
    conn.execute(text("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_company_id_fkey"))
    conn.execute(text("ALTER TABLE channels DROP CONSTRAINT IF EXISTS channels_company_id_fkey"))

    conn.execute(text("DROP INDEX IF EXISTS idx_messages_company"))
    conn.execute(text("DROP INDEX IF EXISTS idx_conversations_company"))
    conn.execute(text("DROP INDEX IF EXISTS idx_channels_company"))

    conn.execute(text("ALTER TABLE messages DROP COLUMN IF EXISTS company_id"))
    conn.execute(text("ALTER TABLE conversations DROP COLUMN IF EXISTS company_id"))
    conn.execute(text("ALTER TABLE channels DROP COLUMN IF EXISTS company_id"))

    print("  [002] Downgrade: RLS, Realtime e colunas company_id removidos")