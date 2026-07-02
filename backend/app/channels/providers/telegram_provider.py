"""
TelegramProvider — stub para implementação futura.

Quando implementar:
1. Registrar webhook no BotFather: /setwebhook
2. parse_incoming: ler update.message.text e update.message.from.id
3. send_message: POST https://api.telegram.org/bot{TOKEN}/sendMessage
4. verify_webhook: Telegram não exige verificação (usa secret_token opcional)
"""

from app.channels.base import ChannelProvider, IncomingMessage
import logging

logger = logging.getLogger(__name__)


class TelegramProvider(ChannelProvider):
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        logger.warning("[Telegram] Provider ainda não implementado")

    async def parse_incoming(self, payload: dict) -> IncomingMessage | None:
        raise NotImplementedError("TelegramProvider ainda não implementado")

    async def send_message(self, to_id: str, content: str) -> bool:
        raise NotImplementedError("TelegramProvider ainda não implementado")

    async def verify_webhook(self, params: dict) -> str | None:
        return None