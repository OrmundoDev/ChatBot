"""
WebChatProvider — stub para implementação futura.

Este canal permitirá que qualquer site incorpore o chatbot
via widget JavaScript, sem depender de WhatsApp ou Telegram.

Quando implementar:
1. parse_incoming: ler payload do widget (session_id, message)
2. send_message: retornar na própria resposta HTTP (WebSocket ou SSE)
3. verify_webhook: não necessário (nossa própria API)
"""

from app.channels.base import ChannelProvider, IncomingMessage
import logging

logger = logging.getLogger(__name__)


class WebChatProvider(ChannelProvider):
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        logger.warning("[WebChat] Provider ainda não implementado")

    async def parse_incoming(self, payload: dict) -> IncomingMessage | None:
        raise NotImplementedError("WebChatProvider ainda não implementado")

    async def send_message(self, to_id: str, content: str) -> bool:
        raise NotImplementedError("WebChatProvider ainda não implementado")

    async def verify_webhook(self, params: dict) -> str | None:
        return None