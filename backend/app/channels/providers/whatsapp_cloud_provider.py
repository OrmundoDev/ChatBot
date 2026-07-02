"""
WhatsAppCloudProvider — canal de comunicação via WhatsApp Cloud API (Meta).

Esta é a API oficial da Meta para WhatsApp Business.

FLUXO COMPLETO:
1. Meta envia GET /webhooks/whatsapp_cloud para verificar o endpoint
   (acontece uma vez na configuração do webhook no painel da Meta)
2. Meta envia POST /webhooks/whatsapp_cloud com mensagens dos usuários
3. Nosso backend processa e responde via Graph API

CREDENCIAIS NECESSÁRIAS (no .env por agora, no banco na Etapa 2):
- WHATSAPP_CLOUD_PHONE_NUMBER_ID: ID do número no painel da Meta
- WHATSAPP_CLOUD_ACCESS_TOKEN: token de acesso (permanent ou temporário)
- WHATSAPP_CLOUD_VERIFY_TOKEN: token que você define para verificação do webhook

Etapa 2: tudo isso virá do campo config (JSON) da tabela channels.
"""

import httpx
from app.channels.base import ChannelProvider, IncomingMessage
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Versão da Graph API — atualize conforme necessário
GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class WhatsAppCloudProvider(ChannelProvider):
    """
    Provedor de canal para a WhatsApp Cloud API (API oficial da Meta).

    Estrutura do webhook de mensagem da Meta:
    {
      "object": "whatsapp_business_account",
      "entry": [{
        "changes": [{
          "value": {
            "metadata": {"phone_number_id": "..."},
            "contacts": [{"wa_id": "5511999999999"}],
            "messages": [{
              "from": "5511999999999",
              "id": "wamid.xxx",
              "type": "text",
              "text": {"body": "Olá"}
            }]
          }
        }]
      }]
    }
    """

    def __init__(self, config: dict | None = None):
        cfg = config or {}

        # Etapa 2: estes valores virão do banco (tabela channels.config).
        self.phone_number_id = (
            cfg.get("phone_number_id")
            or getattr(settings, "WHATSAPP_CLOUD_PHONE_NUMBER_ID", "")
        )
        self.access_token = (
            cfg.get("access_token")
            or getattr(settings, "WHATSAPP_CLOUD_ACCESS_TOKEN", "")
        )
        self.verify_token = (
            cfg.get("verify_token")
            or getattr(settings, "WHATSAPP_CLOUD_VERIFY_TOKEN", "")
        )

    async def verify_webhook(self, params: dict) -> str | None:
        """
        Verifica a autenticidade do webhook da Meta.

        A Meta envia um GET com três parâmetros:
        - hub.mode: sempre "subscribe"
        - hub.verify_token: o token que você configurou no painel da Meta
        - hub.challenge: um número aleatório que você deve devolver

        Se os tokens baterem, devolvemos o hub.challenge para confirmar
        que este endpoint nos pertence. É uma segurança da Meta.
        """
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")

        if mode == "subscribe" and token == self.verify_token:
            logger.info("[WhatsAppCloud] Webhook verificado com sucesso")
            return challenge  # Meta espera receber este valor

        logger.warning(
            f"[WhatsAppCloud] Falha na verificação do webhook. "
            f"Token recebido: '{token}', esperado: '{self.verify_token}'"
        )
        return None

    async def parse_incoming(self, payload: dict) -> IncomingMessage | None:
        """
        Transforma o webhook da Meta em IncomingMessage.

        Ignora:
        - Notificações de status (delivered, read, failed)
        - Mensagens que não são de texto
        - Payloads malformados
        """
        try:
            # Valida estrutura básica do payload da Meta
            if payload.get("object") != "whatsapp_business_account":
                return None

            entries = payload.get("entry", [])
            if not entries:
                return None

            # Pega a primeira mudança (em geral só há uma por webhook)
            value = entries[0].get("changes", [{}])[0].get("value", {})

            # Ignora se não há mensagens (ex: notificações de status)
            messages = value.get("messages", [])
            if not messages:
                return None

            message = messages[0]

            # Só processa mensagens de texto
            if message.get("type") != "text":
                logger.info(
                    f"[WhatsAppCloud] Tipo não suportado ignorado: {message.get('type')}"
                )
                return None

            content = message.get("text", {}).get("body", "").strip()
            if not content:
                return None

            from_id = message.get("from", "")
            message_id = message.get("id", "")

            # Pega o phone_number_id do metadata (confirma qual número recebeu)
            metadata = value.get("metadata", {})
            to_id = metadata.get("phone_number_id", self.phone_number_id)

            return IncomingMessage(
                channel_provider="whatsapp_cloud",
                from_id=from_id,
                to_id=to_id,
                message_id=message_id,
                content=content,
                raw=payload,
            )

        except Exception as e:
            logger.error(
                f"[WhatsAppCloud] Erro ao parsear webhook: {e}", exc_info=True
            )
            return None

    async def send_message(self, to_id: str, content: str) -> bool:
        """
        Envia uma mensagem via Graph API da Meta.

        Args:
            to_id: número do destinatário (ex: "5511999999999")
            content: texto da resposta
        """
        if not self.phone_number_id or not self.access_token:
            logger.error(
                "[WhatsAppCloud] phone_number_id ou access_token não configurados"
            )
            return False

        url = f"{GRAPH_API_BASE}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_id,
            "type": "text",
            "text": {"body": content},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"[WhatsAppCloud] Mensagem enviada para {to_id}")
                return True
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[WhatsAppCloud] Erro HTTP ao enviar mensagem: "
                f"{e.response.status_code} — {e.response.text}"
            )
            return False
        except Exception as e:
            logger.error(
                f"[WhatsAppCloud] Erro ao enviar mensagem: {e}", exc_info=True
            )
            return False