"""
InstagramProvider — stub para implementação futura.

Quando implementar:
1. Configurar webhook no painel da Meta (mesmo fluxo do WhatsApp Cloud)
2. parse_incoming: ler messaging[0].message.text
3. send_message: POST https://graph.facebook.com/v19.0/me/messages
4. verify_webhook: mesmo padrão hub.challenge do WhatsApp Cloud
"""

from app.channels.base import ChannelProvider, IncomingMessage
import logging

logger = logging.getLogger(__name__)


class InstagramProvider(ChannelProvider):
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        logger.warning("[Instagram] Provider ainda não implementado")

    async def parse_incoming(self, payload: dict) -> IncomingMessage | None:
        raise NotImplementedError("InstagramProvider ainda não implementado")

    async def send_message(self, to_id: str, content: str) -> bool:
        raise NotImplementedError("InstagramProvider ainda não implementado")

    async def verify_webhook(self, params: dict) -> str | None:
        return None