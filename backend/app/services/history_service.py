"""
HistoryService — gerencia o histórico real de conversa.

Responsabilidade única:
- Buscar ou criar a conversa ativa pelo session_id
- Carregar as mensagens anteriores para dar memória à IA
- Salvar a interação atual após a IA responder
- Salvar apenas a mensagem do usuário quando o bot está pausado
"""

import time
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation
from app.db.repositories.conversation_repository import ConversationRepository
from app.llm.base import ChatMessage


class HistoryService:

    def __init__(self, db: AsyncSession):
        self.db = db
        # Armazena a conversa ativa internamente para não
        # precisar passá-la em cada chamada de método
        self._conversation: Conversation | None = None

    async def get_or_create_conversation(
        self,
        session_id: str,
        agent_id: UUID | str,
        channel_id: UUID | str | None = None,
        from_id: str | None = None,
    ) -> Conversation:
        """
        Busca a conversa ativa pelo session_id ou cria uma nova.

        Retorna o objeto Conversation completo para que o
        ConversationService possa verificar o campo 'status'
        antes de decidir se a IA deve ou não responder.
        """
        if isinstance(agent_id, str):
            agent_id = UUID(agent_id)
        if isinstance(channel_id, str):
            channel_id = UUID(channel_id)

        conversation = await ConversationRepository.get_or_create(
            db=self.db,
            session_id=session_id,
            agent_id=agent_id,
            channel_id=channel_id,
            from_id=from_id,
        )
        self._conversation = conversation
        return conversation

    async def load(self) -> list[ChatMessage]:
        """
        Carrega o histórico de mensagens da conversa ativa.

        Retorna no formato que o PromptBuilder espera:
        [
          {"role": "user",      "content": "Preciso de um visto"},
          {"role": "assistant", "content": "Para solicitar..."},
          ...
        ]
        O PromptBuilder insere essas mensagens entre o system
        prompt e a pergunta atual — dando memória real à IA.
        """
        if self._conversation is None:
            return []

        t = time.perf_counter()
        messages = await ConversationRepository.get_recent_messages(
            self.db,
            self._conversation.id,
            limit=10,
        )
        print(
            f"[HistoryService] {len(messages)} mensagens carregadas "
            f"em {time.perf_counter() - t:.2f}s"
        )

        return [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

    async def save(self, pergunta: str, resposta: str) -> None:
        """
        Salva a pergunta e a resposta como mensagens separadas.

        Chamado quando o bot respondeu com sucesso.
        Na próxima mensagem do mesmo usuário, estas duas linhas
        aparecerão no load() e darão contexto à IA.
        """
        if self._conversation is None:
            return

        t = time.perf_counter()
        await ConversationRepository.save_messages(
            self.db,
            self._conversation.id,
            pergunta,
            resposta,
        )
        print(f"[HistoryService] Salvo em {time.perf_counter() - t:.2f}s")

    async def save_user_message(self, pergunta: str) -> None:
        """
        Salva apenas a mensagem do usuário, sem resposta da IA.

        Chamado quando conversation.status != 'ai_active'.
        O operador humano verá a mensagem no painel, mas o bot
        não vai responder.
        """
        if self._conversation is None:
            return

        await ConversationRepository.save_user_message(
            self.db,
            self._conversation.id,
            pergunta,
        )