"""
WhatsAppCloudProvider — canal de comunicação via WhatsApp Cloud API (Meta).

Esta é a API oficial da Meta para WhatsApp Business. Também suporta BSPs
(parceiros homologados pela Meta, como a Datafy) que espelham a mesma API
sob uma URL e token próprios — nesse caso, basta configurar `api_base_url`
e `access_token` (o token do parceiro) no `config` do canal, no banco.

FLUXO COMPLETO:
1. Meta (ou o BSP) envia GET /webhooks/whatsapp_cloud para verificar o endpoint
   (acontece uma vez na configuração do webhook)
2. Meta (ou o BSP) envia POST /webhooks/whatsapp_cloud com mensagens dos usuários
3. Nosso backend processa e responde via Graph API (direto ou via BSP)

CREDENCIAIS NECESSÁRIAS (tudo no banco, na tabela channels.config):
- phone_number_id: ID do número (na Meta ou no painel do BSP)
- access_token: token de acesso (da Meta, ou sk_live_xxx de um BSP)
- verify_token: token que você define para verificação do webhook
- api_base_url (opcional): URL base da API. Se omitido, usa a Meta oficial.
  Exemplo para Datafy: "https://cloud.datafyapi.com.br/v1"
"""

import httpx
from app.channels.base import ChannelProvider, IncomingMessage
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Versão e URL padrão da Graph API oficial — usada quando o canal não
# especifica um api_base_url próprio (ex: um BSP) no config.
GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class WhatsAppCloudProvider(ChannelProvider):
    """
    Provedor de canal para a WhatsApp Cloud API — Meta direta ou via BSP.
    """

    def __init__(self, config: dict | None = None):
        cfg = config or {}

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
        # Cada canal pode apontar para uma URL de API diferente (Meta direta
        # ou um BSP homologado, como a Datafy). Padrão: Meta oficial.
        self.api_base = cfg.get("api_base_url") or GRAPH_API_BASE

    async def verify_webhook(self, params: dict) -> str | None:
        """
        Verifica a autenticidade do webhook (Meta ou BSP).

        Envia um GET com três parâmetros:
        - hub.mode: sempre "subscribe"
        - hub.verify_token: o token que você configurou
        - hub.challenge: um número aleatório que você deve devolver
        """
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")

        if mode == "subscribe" and token == self.verify_token:
            logger.info("[WhatsAppCloud] Webhook verificado com sucesso")
            return challenge

        logger.warning(
            f"[WhatsAppCloud] Falha na verificação do webhook. "
            f"Token recebido: '{token}', esperado: '{self.verify_token}'"
        )
        return None

    async def parse_incoming(self, payload: dict) -> IncomingMessage | None:
        """
        Transforma o webhook (Meta ou BSP) em IncomingMessage.
        O formato é idêntico em ambos os casos (BSPs homologados espelham
        o payload oficial da Meta).
        """
        try:
            if payload.get("object") != "whatsapp_business_account":
                return None

            entries = payload.get("entry", [])
            if not entries:
                return None

            value = entries[0].get("changes", [{}])[0].get("value", {})

            messages = value.get("messages", [])
            if not messages:
                return None

            message = messages[0]

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
        Envia uma mensagem via Graph API — direto na Meta ou através de um
        BSP (ex: Datafy), dependendo do api_base configurado neste canal.
        """
        if not self.phone_number_id or not self.access_token:
            logger.error(
                "[WhatsAppCloud] phone_number_id ou access_token não configurados"
            )
            return False

        url = f"{self.api_base}/{self.phone_number_id}/messages"
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
