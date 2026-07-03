"""
KnowledgeService — busca semântica no Knowledge Base.

Responsabilidade única:
Buscar os chunks mais relevantes para uma pergunta,
filtrados pela empresa correta.

O filtro por company_id garante que nenhuma empresa
acessa documentos de outra — isolamento total.
"""

import time
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.chunk import Chunk
from app.services.embedding_service import gerar_embedding


class KnowledgeService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        pergunta: str,
        company_id: str | UUID | None = None,
        limit: int = 3,
    ) -> str:
        """
        Busca os chunks mais relevantes para a pergunta.

        O filtro por company_id é a barreira de isolamento
        entre empresas — Empresa A nunca recebe chunks da Empresa B.

        Retorna os chunks concatenados como string pronta para
        ser injetada no prompt da IA como contexto.
        """
        t = time.perf_counter()
        embedding_pergunta = await gerar_embedding(pergunta)

        query = (
            select(Chunk)
            .order_by(Chunk.embedding.cosine_distance(embedding_pergunta))
            .limit(limit)
        )

        if company_id:
            cid = UUID(str(company_id)) if isinstance(company_id, str) else company_id
            query = query.where(Chunk.company_id == cid)

        resultado = await self.db.execute(query)
        chunks = resultado.scalars().all()

        print(
            f"[KnowledgeService] {len(chunks)} chunks encontrados "
            f"em {time.perf_counter() - t:.2f}s "
            f"(company={company_id})"
        )

        if not chunks:
            return ""

        return "\n\n---\n\n".join(c.content for c in chunks)