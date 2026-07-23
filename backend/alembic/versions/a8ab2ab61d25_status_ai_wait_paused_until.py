"""status_ai_wait_paused_until

Revision ID: a8ab2ab61d25
Revises: 37522959265b
Create Date: 2026-07-23

Migração 003 — adiciona o modo de pausa temporária (ai_wait) ao status
das conversas.

O que muda:
1. Coluna nova `conversations.paused_until` (timestamp, opcional) — só
   é usada quando status='ai_wait'; guarda até quando a IA deve
   permanecer pausada antes de voltar sozinha.
2. Renomeia o vocabulário de status: os valores antigos 'human_active'
   e 'waiting_human' (qualquer conversa que já estivesse com a IA
   pausada, hoje em produção) viram 'ai_off' — pausa sem prazo,
   precisa de reativação manual. Isso preserva o comportamento atual
   dessas conversas (bot continua não respondendo), só troca o nome.
3. O status 'ai_active' não muda.

Novos 3 valores possíveis de conversations.status a partir daqui:
'ai_active' | 'ai_off' | 'ai_wait'
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = 'a8ab2ab61d25'
down_revision: Union[str, Sequence[str], None] = '37522959265b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Coluna nova, usada só quando status='ai_wait'
    conn.execute(text(
        "ALTER TABLE conversations ADD COLUMN paused_until TIMESTAMPTZ"
    ))

    # 2. Migra os dados existentes: conversas já pausadas em produção
    # (human_active/waiting_human) viram ai_off, preservando o
    # comportamento (bot continua não respondendo), só o nome muda.
    conn.execute(text(
        "UPDATE conversations SET status = 'ai_off' "
        "WHERE status IN ('human_active', 'waiting_human')"
    ))


def downgrade() -> None:
    conn = op.get_bind()

    # Reverte o mais próximo possível do estado original — não é
    # perfeitamente reversível (não temos como saber se uma conversa
    # ai_off era antes human_active ou waiting_human), mas mantém o
    # comportamento de "IA pausada" preservado.
    conn.execute(text(
        "UPDATE conversations SET status = 'human_active' "
        "WHERE status IN ('ai_off', 'ai_wait')"
    ))

    conn.execute(text(
        "ALTER TABLE conversations DROP COLUMN paused_until"
    ))
