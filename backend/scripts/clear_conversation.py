"""
Script para limpar o histórico de uma conversa específica.

Uso (modo a seco — só mostra o que seria apagado, não apaga nada):
    python -m scripts.clear_conversation --numero 5511999999999

Uso real (apaga de fato):
    python -m scripts.clear_conversation --numero 5511999999999 --confirmar

Se o mesmo número já conversou com mais de uma empresa na plataforma,
o script recusa apagar sem você especificar qual empresa (--company-id),
pra nunca apagar a conversa errada por engano:
    python -m scripts.clear_conversation --numero 5511999999999 \\
        --company-id UUID_DA_EMPRESA --confirmar

Canal diferente do padrão (whatsapp_cloud):
    python -m scripts.clear_conversation --numero 5511999999999 --canal evolution --confirmar

Por que existe: ao testar a Base de Conhecimento pelo WhatsApp, o
HistoryService carrega as últimas mensagens da conversa e as envia como
contexto pra IA — então perguntas de teste antigas continuam
"influenciando" as respostas seguintes, mesmo depois de você atualizar
os documentos. Esse script apaga só as mensagens daquela conversa
específica (por número de telefone + empresa), sem afetar nenhuma
outra conversa ou dado.

Não apaga a conversa em si (a linha em 'conversations'), só as
mensagens — e reseta o status para 'ai_active', por segurança, caso
algum teste anterior tenha deixado a conversa pausada.
"""

import asyncio
import argparse
from uuid import UUID

from sqlalchemy import select, delete

from app.db.session import AsyncSessionLocal
from app.db.models.conversation import Conversation
from app.db.models.message import Message


async def limpar(session_id: str, confirmar: bool, company_id: UUID | None) -> None:
    async with AsyncSessionLocal() as sessao:
        query = select(Conversation).where(Conversation.session_id == session_id)
        if company_id is not None:
            query = query.where(Conversation.company_id == company_id)

        resultado = await sessao.execute(query)
        conversas = resultado.scalars().all()

        if not conversas:
            filtro = f" na empresa {company_id}" if company_id else ""
            print(f"⚠️  Nenhuma conversa encontrada com session_id='{session_id}'{filtro}")
            return

        # Ambiguidade: o mesmo número conversou com mais de uma empresa
        # e nenhuma foi especificada — recusa apagar, só avisa.
        if len(conversas) > 1 and company_id is None:
            print(
                f"⚠️  Esse número aparece em {len(conversas)} empresas "
                f"diferentes. Nada foi apagado. Rode de novo passando "
                f"--company-id pra escolher qual:\n"
            )
            for conversa in conversas:
                print(
                    f"   - company_id={conversa.company_id} "
                    f"(conversation_id={conversa.id}, status='{conversa.status}')"
                )
            return

        for conversa in conversas:
            resultado_msgs = await sessao.execute(
                select(Message).where(Message.conversation_id == conversa.id)
            )
            total_mensagens = len(resultado_msgs.scalars().all())

            print(
                f"🗂️  Conversa {conversa.id} (empresa {conversa.company_id}, "
                f"status atual: '{conversa.status}') — "
                f"{total_mensagens} mensagem(ns) encontrada(s)"
            )

            if not confirmar:
                print(
                    "   (modo a seco — nada foi apagado. "
                    "Rode de novo com --confirmar para executar)"
                )
                continue

            await sessao.execute(
                delete(Message).where(Message.conversation_id == conversa.id)
            )
            conversa.status = "ai_active"
            print(
                f"   ✅ {total_mensagens} mensagem(ns) apagada(s). "
                f"Status resetado para 'ai_active'."
            )

        if confirmar:
            await sessao.commit()


async def main():
    parser = argparse.ArgumentParser(
        description="Apaga o historico de mensagens de uma conversa "
                     "especifica (uso: testes de Base de Conhecimento)"
    )
    parser.add_argument(
        "--numero",
        required=True,
        help="Numero de telefone, sem prefixo do canal (ex: 5511999999999)",
    )
    parser.add_argument(
        "--canal",
        default="whatsapp_cloud",
        help="Provider do canal (padrao: whatsapp_cloud)",
    )
    parser.add_argument(
        "--company-id",
        default=None,
        help="UUID da empresa (opcional, mas obrigatorio se o mesmo "
             "numero existir em mais de uma empresa)",
    )
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help="Executa de verdade. Sem essa flag, so mostra o que seria apagado.",
    )
    args = parser.parse_args()

    company_id = None
    if args.company_id:
        try:
            company_id = UUID(args.company_id)
        except ValueError as e:
            print(f"❌ UUID inválido em --company-id: {e}")
            return

    session_id = f"{args.canal}:{args.numero}"
    print(f"🔎 Procurando conversa: session_id='{session_id}'\n")
    await limpar(session_id, args.confirmar, company_id)


if __name__ == "__main__":
    asyncio.run(main())
