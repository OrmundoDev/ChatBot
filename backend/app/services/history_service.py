"""
HistoryService — gerencia o histórico de conversa de uma sessão.

Responsabilidade única:
Carregar as mensagens anteriores de uma sessão e salvar
novas mensagens ao final de cada interação.

AGORA (Etapa 1):
- load() retorna lista vazia (cada mensagem ainda é stateless)
- save() persiste na tabela 'conversas' atual (já existente)

ETAPA 4:
- load() vai buscar as últimas N mensagens da tabela 'mensagens'
  filtradas por session_id, para construir a memória da conversa.
- save() vai salvar cada mensagem (user e assistant) separadamente
  na tabela 'mensagens' com o session_id correto.

Com isso, o chatbot vai conseguir entender referências como:
  "Quero marcar uma tomografia."
  "Pode ser de manhã?"
Sem precisar repetir o contexto.
"""

import time
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversa
from app.llm.base import ChatMessage


class HistoryService:
    """
    Gerencia o histórico de conversas de uma sessão.

    Recebe a sessão de banco via construtor pelo mesmo motivo
    do KnowledgeService: compartilhar a sessão da requisição.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load(self, session_id: str | None) -> list[ChatMessage]:
        """
        Carrega o histórico de mensagens de uma sessão.

        Args:
            session_id: identificador da sessão de conversa.
                        Etapa 4: este ID será usado para buscar
                        as mensagens anteriores no banco.

        Returns:
            Lista de ChatMessage no formato que o PromptBuilder espera.
            Por enquanto sempre vazia — sem memória entre mensagens.
        """
        # ── Etapa 4: substituir por: ─────────────────────────────────────
        # mensagens = await self.db.execute(
        #     select(Mensagem)
        #     .where(Mensagem.conversa_id == session_id)
        #     .order_by(Mensagem.criado_em.asc())
        #     .limit(10)   # janela de contexto
        # )
        # return [
        #     {"role": m.role, "content": m.conteudo}
        #     for m in mensagens.scalars().all()
        # ]
        # ─────────────────────────────────────────────────────────────────
        return []

    async def save(
        self,
        session_id: str | None,
        pergunta: str,
        resposta: str,
    ) -> None:
        """
        Persiste a interação atual no banco.

        Args:
            session_id: identificador da sessão (Etapa 4).
            pergunta: mensagem enviada pelo usuário.
            resposta: resposta gerada pela IA.

        AGORA: salva na tabela 'conversas' (formato atual).
        ETAPA 4: salva duas linhas na tabela 'mensagens'
                 (uma com role='user', outra com role='assistant'),
                 ambas vinculadas ao session_id.
        """
        t = time.perf_counter()

        # Persistência temporária na tabela atual enquanto Etapa 4 não chega
        nova_conversa = Conversa(pergunta=pergunta, resposta=resposta)
        self.db.add(nova_conversa)
        await self.db.commit()

        print(f"[HistoryService][TEMPO] Save: {time.perf_counter() - t:.2f}s")
