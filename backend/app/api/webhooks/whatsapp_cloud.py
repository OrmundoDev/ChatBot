"""
Webhook do WhatsApp Cloud API (Meta).

GET /webhooks/whatsapp_cloud → verificação do endpoint (uma vez só)
POST /webhooks/whatsapp_cloud → mensagens dos usuários (contínuo)
"""

import logging
from fastapi import APIRouter, Request, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.factory import get_channel_provider
from app.db.repositories.channel_repository import ChannelRepository
from app.services.conversation_service import ConversationService
from app.api.dependencies.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/whatsapp_cloud")
async def verify_whatsapp_cloud_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Verificação do webhook pela Meta.
    Chamada uma vez para cada cliente, quando ele configura o webhook
    no próprio painel do Meta for Developers. Busca no banco qual
    canal tem esse verify_token, já que a Meta não informa o
    phone_number_id nessa chamada.
    """
    params = dict(request.query_params)
    token = params.get("hub.verify_token")

    channel = (
        await ChannelRepository.get_by_verify_token(db, "whatsapp_cloud", token)
        if token else None
    )
    config = channel.config if channel else None

    provider = get_channel_provider("whatsapp_cloud", config=config)
    challenge = await provider.verify_webhook(params)

    if challenge:
        return Response(content=challenge, media_type="text/plain")

    from fastapi import HTTPException
    raise HTTPException(status_code=403, detail="Falha na verificação")


@router.post("/whatsapp_cloud")
async def receive_whatsapp_cloud_message(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe mensagens do WhatsApp Cloud.
    Sempre retorna 200 — a Meta considera qualquer outro status como falha.
    """
    try:
        payload = await request.json()

        # Extrai o phone_number_id para identificar o canal no banco
        phone_number_id = (
            payload.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
            .get("metadata", {})
            .get("phone_number_id", "")
        )

        # Busca o canal no banco pelo identifier
        channel = await ChannelRepository.get_by_identifier(
            db, "whatsapp_cloud", phone_number_id
        )

        # Config: prioriza banco, fallback para .env (enquanto não migrado)
        config = channel.config if channel else None
        agent_id = channel.agent_id if channel else None
        channel_id = channel.id if channel else None

        provider = get_channel_provider("whatsapp_cloud", config=config)
        incoming = await provider.parse_incoming(payload)

        if incoming is None:
            return Response(content="OK", status_code=200)

        logger.info(f"[WhatsAppCloud] Mensagem de {incoming.from_id}")

        service = ConversationService(db=db)
        resposta = await service.handle_message(
            pergunta=incoming.content,
            session_id=incoming.session_id,
            agent_id=agent_id,
            channel_id=channel_id,
            from_id=incoming.from_id,
            channel_provider="whatsapp_cloud",
        )

        # Só envia resposta se o bot estiver ativo
        if resposta is not None:
            await provider.send_message(incoming.from_id, resposta)

    except Exception as e:
        logger.error(f"[WhatsAppCloud] Erro: {e}", exc_info=True)

    return Response(content="OK", status_code=200)