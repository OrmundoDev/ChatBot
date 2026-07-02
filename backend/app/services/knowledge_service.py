"""
KnowledgeService — busca semântica no Knowledge Base.

Responsabilidade única:
Dado uma pergunta e opcionalmente um company_id, retorna
o contexto relevante encontrado nos documentos da empresa.

AGORA (Etapa 1):
Busca em todos os chunks, sem filtro de empresa
(só existe uma empresa por enquanto).

ETAPA 3:
O parâmetro company_id vai ser usado no WHERE da query para
garantir isolamento total entre empresas. Nenhum outro arquivo
vai precisar mudar — só este método aqui.
"""

import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import DocumentoChunk
from app.services.embedding_service import gerar_embedding


class KnowledgeService:
    """
    Encapsula a busca vetorial no banco de dados.

    Recebe a sessão de banco via construtor para que o
    ConversationService controle o ciclo de vida da sessão
    (padrão Unit of Work — todos os serviços da mesma
    requisição compartilham a mesma sessão).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        pergunta: str,
        company_id: str | None = None,
        limit: int = 3,
    ) -> str:
        """
        Busca os chunks mais relevantes para a pergunta.

        Args:
            pergunta: texto da mensagem do usuário.
            company_id: ID da empresa para filtrar documentos.
                        Etapa 3: este parâmetro ativa o isolamento.
                        Por agora: ignorado (busca tudo).
            limit: número máximo de chunks retornados.

        Returns:
            String com os chunks concatenados, prontos para
            serem injetados no prompt como contexto.
            Retorna string vazia se nenhum chunk for encontrado.
        """
        t = time.perf_counter()

        # ── 1. Gerar embedding da pergunta ────────────────────────────────
        embedding_pergunta = await gerar_embedding(pergunta)

        # ── 2. Buscar chunks mais similares ───────────────────────────────
        #
        # Etapa 3: adicionar filtro de empresa aqui:
        # .where(DocumentoChunk.company_id == company_id)
        #
        resultado = await self.db.execute(
            select(DocumentoChunk)
            .order_by(DocumentoChunk.embedding.cosine_distance(embedding_pergunta))
            .limit(limit)
        )
        chunks = resultado.scalars().all()

        print(f"[KnowledgeService][TEMPO] Busca RAG: {time.perf_counter() - t:.2f}s "
              f"({len(chunks)} chunks encontrados)")

        if not chunks:
            return ""

        # ── 3. Concatenar e devolver como string ──────────────────────────
        return "\n\n---\n\n".join(c.conteudo for c in chunks)
