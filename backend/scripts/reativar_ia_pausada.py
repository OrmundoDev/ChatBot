"""
Script de reativação automática do bot após pausa temporária (ai_wait).

Uso:
    python -m scripts.reativar_ia_pausada

O que faz: procura todas as conversas com status='ai_wait' cujo prazo
(paused_until) já venceu, e reativa a IA (status='ai_active',
paused_until=NULL) nelas.

Feito para rodar periodicamente via crontab da VPS (ex: a cada minuto),
não interativamente. Não imprime nada se não houver nenhuma conversa
vencida — só reporta quando de fato reativa alguma.
"""

import asyncio

from sqlalchemy import update, func

from app.db.session import AsyncSessionLocal
from app.db.models.conversation import Conversation


async def main():
    async with AsyncSessionLocal() as sessao:
        resultado = await sessao.execute(
            update(Conversation)
            .where(Conversation.status == "ai_wait")
            .where(Conversation.paused_until <= func.now())
            .values(status="ai_active", paused_until=None)
        )
        await sessao.commit()

        if resultado.rowcount:
            print(
                f"✅ {resultado.rowcount} conversa(s) reativada(s) "
                f"automaticamente (prazo de ai_wait vencido)"
            )


if __name__ == "__main__":
    asyncio.run(main())
