"""
Webhook do WhatsApp Cloud API (Meta).

Duas rotas:
- GET  /webhooks/whatsapp_cloud  → verificação do endpoint (uma vez só)
- POST /webhooks/whatsapp_cloud  → mensagens dos usuários (contínuo)

Etapa 2: o phone_number_id do payload será usado para buscar
         qual channel/agent está associado a este número no banco.
"""

import logging
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.factory import get_channel_provider
from app.services.conversation_service import ConversationService
from app.api.dependencies.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/whatsapp_cloud")
async def verify_whatsapp_cloud_webhook(request: Request):
    """
    Verificação do webhook pela Meta.

    A Meta faz esta chamada uma única vez quando você configura
    o webhook no painel de desenvolvedor. Devemos retornar o
    hub.challenge para confirmar que o endpoint é nosso.
    """
    params = dict(request.query_params)
    logger.info(f"[WhatsAppCloud] Solicitação de verificação recebida: {params}")

    provider = get_channel_provider("whatsapp_cloud")
    challenge = await provider.verify_webhook(params)

    if challenge:
        # Retorna o challenge como texto simples — exigência da Meta
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Falha na verificação do webhook")


@router.post("/whatsapp_cloud")
async def receive_whatsapp_cloud_message(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe mensagens do WhatsApp Cloud API.

    IMPORTANTE: Sempre retorna 200 imediatamente.
    A Meta interpreta qualquer status != 200 como falha e
    tentará reenviar. Erros internos são logados, não expostos.

    Etapa 2: vai buscar o channel e agent no banco pelo phone_number_id.
    """
    # Retornamos 200 para a Meta imediatamente (requisito deles)
    # O processamento acontece antes, mas qualquer erro é contido
    try:
        payload = await request.json()
        logger.info(f"[WhatsAppCloud] Webhook recebido")

        provider = get_channel_provider("whatsapp_cloud")
        incoming = await provider.parse_incoming(payload)

        if incoming is None:
            # Mensagem ignorada (status, mídia, etc.) — OK para a Meta
            return Response(content="OK", status_code=200)

        logger.info(
            f"[WhatsAppCloud] Mensagem de {incoming.from_id}: "
            f"{incoming.content[:50]}..."
        )

        # Processa com o ConversationService
        service = ConversationService(db=db)
        resposta = await service.handle_message(
            pergunta=incoming.content,
            session_id=incoming.session_id,
            chatbot_id=incoming.chatbot_id,
            channel_provider="whatsapp_cloud",
        )

        # Envia a resposta de volta ao usuário
        enviado = await provider.send_message(
            to_id=incoming.from_id,
            content=resposta,
        )

        if not enviado:
            logger.error(
                f"[WhatsAppCloud] Falha ao enviar resposta para {incoming.from_id}"
            )

    except Exception as e:
        # Loga o erro mas retorna 200 para não travar os reenvios da Meta
        logger.error(
            f"[WhatsAppCloud] Erro no processamento do webhook: {e}",
            exc_info=True,
        )

    return Response(content="OK", status_code=200)