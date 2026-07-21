"""
ConversationRepository — queries das tabelas conversations e messages.
"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.conversation import Conversation
from app.db.models.message import Message


class ConversationRepository:

    @staticmethod
    async def get_or_create(
        db: AsyncSession,
        session_id: str,
        agent_id: UUID,
        company_id: UUID,
        channel_id: UUID | None = None,
        from_id: str | None = None,
    ) -> Conversation:
        """
        Busca uma conversa ativa pelo session_id ou cria uma nova.

        O session_id é a chave: "whatsapp_cloud:5511999999999".
        Na próxima mensagem do mesmo número, reutilizamos a mesma
        conversa — garantindo continuidade do histórico e do status.

        flush() gera o UUID sem commitar a transação.
        O commit acontece no save_messages() ou save_user_message().
        """
        result = await db.execute(
            select(Conversation)
            .where(Conversation.session_id == session_id)
            .where(Conversation.agent_id == agent_id)
            .where(Conversation.status.in_(["ai_active", "human_active", "waiting_human"]))
            .limit(1)
        )
        conversation = result.scalar_one_or_none()

        if conversation is None:
            conversation = Conversation(
                agent_id=agent_id,
                company_id=company_id,
                channel_id=channel_id,
                session_id=session_id,
                from_id=from_id,
                status="ai_active",
            )
            db.add(conversation)
            await db.flush()

        return conversation

    @staticmethod
    async def get_recent_messages(
        db: AsyncSession,
        conversation_id: UUID,
        limit: int = 10,
    ) -> list[Message]:
        """
        Retorna as N mensagens mais recentes da conversa.

        Limite de 10 para não exceder a janela de contexto do modelo.
        Em conversas longas, apenas as últimas 10 mensagens são
        incluídas no prompt enviado à IA.
        """
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def save_messages(
        db: AsyncSession,
        conversation_id: UUID,
        company_id: UUID,
        pergunta: str,
        resposta: str,
    ) -> None:
        """
        Salva a pergunta e a resposta como mensagens separadas.

        Duas linhas na tabela messages:
        - role='user'      → o que o usuário enviou
        - role='assistant' → o que a IA respondeu
        """
        db.add(Message(
            conversation_id=conversation_id,
            company_id=company_id,
            role="user",
            content=pergunta,
        ))
        db.add(Message(
            conversation_id=conversation_id,
            company_id=company_id,
            role="assistant",
            content=resposta,
        ))
        await db.commit()

    @staticmethod
    async def save_user_message(
        db: AsyncSession,
        conversation_id: UUID,
        company_id: UUID,
        content: str,
    ) -> None:
        """
        Salva apenas a mensagem do usuário (sem resposta da IA).

        Usado quando conversation.status != 'ai_active'.
        O operador humano verá a mensagem no painel mas o bot
        não responde.
        """
        db.add(Message(
            conversation_id=conversation_id,
            company_id=company_id,
            role="user",
            content=content,
        ))
        await db.commit()
