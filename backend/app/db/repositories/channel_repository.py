"""
ChannelRepository — queries da tabela channels.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.channel import Channel


class ChannelRepository:

    @staticmethod
    async def get_by_identifier(
        db: AsyncSession,
        provider: str,
        identifier: str,
    ) -> Channel | None:
        """
        Busca um canal pelo provider e identifier.

        Chamado pelos webhooks para descobrir qual agente deve
        responder, baseado em qual número/instância recebeu a mensagem.

        Exemplo:
        - Chega webhook do WhatsApp Cloud com phone_number_id = "12345"
        - Buscamos: provider="whatsapp_cloud", identifier="12345"
        - Retornamos o channel com agent_id e config do banco
        - Passamos agent_id para o ConversationService
        """
        result = await db.execute(
            select(Channel)
            .where(Channel.provider == provider)
            .where(Channel.identifier == identifier)
            .where(Channel.status == "active")
        )
        return result.scalar_one_or_none()