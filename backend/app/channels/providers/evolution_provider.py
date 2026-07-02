"""
EvolutionProvider — canal de comunicação via Evolution API.

A Evolution API emula o WhatsApp Web para enviar e receber mensagens.

MODO DE USO 1 (atual, via n8n — não muda nada):
  WhatsApp → Evolution → n8n → POST /chat → n8n → Evolution → WhatsApp
  Este provider não é usado neste modo.

MODO DE USO 2 (novo, webhook direto — opcional):
  WhatsApp → Evolution → POST /webhooks/evolution → EvolutionProvider → ConversationService
  Este provider é usado neste modo.

Etapa 2: as configurações (api_url, api_key, instance) virão do
         campo config (JSON) da tabela channels no banco de dados.
         Por enquanto vêm do .env.
"""

import httpx
from app.channels.base import ChannelProvider, IncomingMessage
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EvolutionProvider(ChannelProvider):
    """
    Provedor de canal para a Evolution API.

    Estrutura esperada do webhook da Evolution API:
    {
      "event": "messages.upsert",
      "data": {
        "key": {
          "remoteJid": "5511999999999@s.whatsapp.net",
          "fromMe": false,
          "id": "ABCD1234"
        },
        "message": {
          "conversation": "Olá, preciso de ajuda"
        }
      }
    }
    """

    def __init__(self, config: dict | None = None):
        cfg = config or {}

        # Etapa 2: estes valores virão do banco (tabela channels.config).
        # Por agora, fallback para variáveis de ambiente.
        self.api_url = cfg.get("api_url") or getattr(settings, "EVOLUTION_API_URL", "")
        self.api_key = cfg.get("api_key") or getattr(settings, "EVOLUTION_API_KEY", "")
        self.instance = cfg.get("instance") or getattr(settings, "EVOLUTION_INSTANCE", "")

    async def parse_incoming(self, payload: dict) -> IncomingMessage | None:
        """
        Transforma o webhook da Evolution API em IncomingMessage.

        Ignora:
        - Mensagens enviadas pelo próprio bot (fromMe: true)
        - Eventos que não são mensagens de texto
        - Mensagens com conteúdo vazio
        """
        try:
            # Ignora eventos que não são mensagens
            if payload.get("event") != "messages.upsert":
                return None

            data = payload.get("data", {})
            key = data.get("key", {})

            # Ignora mensagens enviadas pelo próprio bot
            if key.get("fromMe", False):
                return None

            # Extrai o número do remetente (remove o sufixo @s.whatsapp.net)
            remote_jid = key.get("remoteJid", "")
            from_number = remote_jid.replace("@s.whatsapp.net", "").replace("@g.us", "")

            if not from_number:
                return None

            # Extrai o texto da mensagem
            # A Evolution pode enviar em diferentes campos dependendo do tipo
            message_obj = data.get("message", {})
            content = (
                message_obj.get("conversation")
                or message_obj.get("extendedTextMessage", {}).get("text")
                or ""
            ).strip()

            # Ignora mensagens sem texto (áudio, imagem, sticker, etc.)
            if not content:
                logger.info(f"[Evolution] Mensagem sem texto ignorada de {from_number}")
                return None

            message_id = key.get("id", "")

            return IncomingMessage(
                channel_provider="evolution",
                from_id=from_number,
                to_id=self.instance,
                message_id=message_id,
                content=content,
                raw=payload,
            )

        except Exception as e:
            logger.error(f"[Evolution] Erro ao parsear webhook: {e}", exc_info=True)
            return None

    async def send_message(self, to_id: str, content: str) -> bool:
        """
        Envia uma mensagem via Evolution API.

        Args:
            to_id: número do destinatário (somente dígitos, ex: "5511999999999")
            content: texto da resposta
        """
        if not self.api_url or not self.instance:
            logger.error("[Evolution] api_url ou instance não configurados")
            return False

        url = f"{self.api_url}/message/sendText/{self.instance}"
        headers = {"apikey": self.api_key, "Content-Type": "application/json"}
        payload = {
            "number": to_id,
            "text": content,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"[Evolution] Mensagem enviada para {to_id}")
                return True
        except Exception as e:
            logger.error(f"[Evolution] Erro ao enviar mensagem: {e}", exc_info=True)
            return False

    async def verify_webhook(self, params: dict) -> str | None:
        """
        A Evolution API não exige verificação de webhook.
        Retorna None (sem ação necessária).
        """
        return None