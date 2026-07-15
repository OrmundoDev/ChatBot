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
        """
        result = await db.execute(
            select(Channel)
            .where(Channel.provider == provider)
            .where(Channel.identifier == identifier)
            .where(Channel.status == "active")
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_verify_token(
        db: AsyncSession,
        provider: str,
        verify_token: str,
    ) -> Channel | None:
        """
        Busca um canal pelo verify_token guardado em config (JSON).

        Usado na verificação do webhook (GET), que a Meta chama sem
        informar qual phone_number_id está sendo configurado — só o
        token. Por isso a busca precisa ser pelo token, não pelo
        identifier.
        """
        result = await db.execute(
            select(Channel)
            .where(Channel.provider == provider)
            .where(Channel.config["verify_token"].astext == verify_token)
            .where(Channel.status == "active")
        )
        return result.scalar_one_or_none()
