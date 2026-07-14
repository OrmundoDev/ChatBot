"""
Webhook direto da Evolution API (opcional — n8n continua funcionando via /chat).

Use este endpoint quando quiser eliminar o n8n do fluxo de mensagens.
Para ativar, configure na Evolution API:
  URL do webhook: http://SEU_IP:8000/webhooks/evolution
  Eventos: MESSAGES_UPSERT
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


@router.post("/evolution")
async def receive_evolution_message(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe webhooks diretamente da Evolution API.
    Coexiste com o n8n atual sem conflito.
    """
    try:
        payload = await request.json()

        # Extrai o nome da instância para identificar o canal no banco
        instance = payload.get("instance", "")

        # Busca o canal no banco pelo identifier
        channel = await ChannelRepository.get_by_identifier(
            db, "evolution", instance
        )

        config = channel.config if channel else None
        agent_id = channel.agent_id if channel else None
        channel_id = channel.id if channel else None

        provider = get_channel_provider("evolution", config=config)
        incoming = await provider.parse_incoming(payload)

        if incoming is None:
            return Response(content="OK", status_code=200)

        logger.info(f"[Evolution] Mensagem de {incoming.from_id}")

        service = ConversationService(db=db)
        resposta = await service.handle_message(
            pergunta=incoming.content,
            session_id=incoming.session_id,
            agent_id=agent_id,
            channel_id=channel_id,
            from_id=incoming.from_id,
            channel_provider="evolution",
        )
        
        if resposta is not None:
            await provider.send_message(incoming.from_id, resposta)

    except Exception as e:
        logger.error(f"[Evolution] Erro: {e}", exc_info=True)

    return Response(content="OK", status_code=200)