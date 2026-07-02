"""
Webhook direto da Evolution API.

Este endpoint é OPCIONAL — o n8n atual continua funcionando via /chat.
Use este endpoint quando quiser eliminar o n8n do fluxo de mensagens
e receber webhooks diretamente da Evolution API.

Para ativar, configure na Evolution API:
  URL do webhook: http://SEU_IP:8000/webhooks/evolution
  Eventos: MESSAGES_UPSERT
"""

import logging
from fastapi import APIRouter, Request, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.factory import get_channel_provider
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
    Recebe webhooks diretamente da Evolution API (sem n8n).

    Se você ainda usa n8n, este endpoint pode coexistir sem conflito.
    A Evolution API pode ter múltiplos webhooks configurados.

    Etapa 2: vai buscar o channel e agent no banco pela instance.
    """
    try:
        payload = await request.json()

        provider = get_channel_provider("evolution")
        incoming = await provider.parse_incoming(payload)

        if incoming is None:
            return Response(content="OK", status_code=200)

        logger.info(
            f"[Evolution] Mensagem de {incoming.from_id}: "
            f"{incoming.content[:50]}..."
        )

        service = ConversationService(db=db)
        resposta = await service.handle_message(
            pergunta=incoming.content,
            session_id=incoming.session_id,
            chatbot_id=incoming.chatbot_id,
            channel_provider="evolution",
        )

        enviado = await provider.send_message(
            to_id=incoming.from_id,
            content=resposta,
        )

        if not enviado:
            logger.error(
                f"[Evolution] Falha ao enviar resposta para {incoming.from_id}"
            )

    except Exception as e:
        logger.error(
            f"[Evolution] Erro no processamento do webhook: {e}",
            exc_info=True,
        )

    return Response(content="OK", status_code=200)