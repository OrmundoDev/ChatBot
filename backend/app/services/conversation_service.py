"""
ConversationService — coordenador do fluxo de conversa.

Responsabilidade única:
Orquestrar os serviços em ordem correta para transformar
uma mensagem do usuário em uma resposta da IA.

Inclui verificação do status da conversa:
- 'ai_active'    → fluxo completo (IA responde)
- 'human_active' → salva mensagem, retorna None (humano atende)
- 'waiting_human'→ salva mensagem, retorna None (aguarda humano)
"""

import time
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_service import AgentService
from app.services.knowledge_service import KnowledgeService
from app.services.history_service import HistoryService
from app.services.prompt_builder import PromptBuilder
from app.llm.factory import get_llm_provider


class ConversationService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def handle_message(
        self,
        pergunta: str,
        session_id: str = "default:anonymous",
        agent_id: UUID | str | None = None,
        channel_id: UUID | str | None = None,
        from_id: str | None = None,
        channel_provider: str | None = None,
    ) -> str | None:
        """
        Processa uma mensagem e retorna a resposta da IA.

        Retorna:
            str  → resposta da IA (bot ativo)
            None → bot pausado (mensagem salva, nenhuma resposta enviada)
        """
        inicio = time.perf_counter()

        if channel_provider:
            print(
                f"[ConversationService] Canal: {channel_provider} "
                f"| Sessão: {session_id}"
            )

        # ── 1. Qual agente responde? ───────────────────────────────────────
        # Busca no banco pelo agent_id ou retorna o agente padrão
        agente = await AgentService.load(self.db, agent_id)

        # ── 2. Qual conversa está ativa? ──────────────────────────────────
        # Busca pelo session_id ou cria uma nova com status='ai_active'
        history_svc = HistoryService(self.db)
        conversation = await history_svc.get_or_create_conversation(
            session_id=session_id,
            agent_id=UUID(agente.agent_id),
            channel_id=channel_id,
            from_id=from_id,
        )

        # ── 3. O bot pode responder? ──────────────────────────────────────
        # Verifica o status da conversa antes de acionar a IA
        if conversation.status != "ai_active":
            print(
                f"[ConversationService] Bot pausado "
                f"(status={conversation.status}) — salvando mensagem sem resposta"
            )
            # Salva a mensagem do usuário para o operador humano ver
            await history_svc.save_user_message(pergunta)
            # Retorna None: o webhook não vai enviar resposta
            return None

        # ── 4. O que os documentos sabem sobre isso? ──────────────────────
        knowledge = KnowledgeService(self.db)
        contexto = await knowledge.search(
            pergunta,
            company_id=agente.company_id,
        )

        # ── 5. O que foi dito antes nesta sessão? ─────────────────────────
        historico = await history_svc.load()

        # ── 6. Monta o pacote de mensagens para a IA ──────────────────────
        messages = PromptBuilder.build(agente, contexto, historico, pergunta)

        # ── 7. Qual IA usa? Chama e gera a resposta ───────────────────────
        provider = get_llm_provider(
            agente.provider_name,
            model=agente.model,
        )
        resposta = await provider.generate(
            messages,
            temperature=agente.temperature,
        )

        # ── 8. Salva pergunta + resposta no histórico ─────────────────────
        await history_svc.save(pergunta, resposta)

        print(
            f"[ConversationService] TOTAL: "
            f"{time.perf_counter() - inicio:.2f}s"
        )
        return resposta