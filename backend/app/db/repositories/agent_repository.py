"""
AgentRepository — queries da tabela agents.
"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.agent import Agent


class AgentRepository:

    @staticmethod
    async def get_by_id(db: AsyncSession, agent_id: UUID) -> Agent | None:
        """Busca agente pelo UUID."""
        return await db.get(Agent, agent_id)

    @staticmethod
    async def get_default(db: AsyncSession) -> Agent | None:
        """
        Retorna o primeiro agente ativo encontrado.

        Usado como fallback para o /chat via n8n, que não especifica
        qual agente deve responder.
        """
        result = await db.execute(
            select(Agent)
            .where(Agent.status == "active")
            .limit(1)
        )
        return result.scalar_one_or_none()