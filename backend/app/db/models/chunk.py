from uuid import uuid4
from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.db.base import Base


class Chunk(Base):
    """
    Fragmento de documento com seu embedding vetorial.

    Por que company_id aparece aqui além de estar no document:
    A busca RAG executa milhares de vezes por dia. Se company_id
    só estivesse em 'documents', cada busca precisaria de um JOIN.
    Com company_id diretamente no chunk, a query de busca fica:

    SELECT * FROM chunks
    WHERE company_id = 'uuid-da-empresa'
    ORDER BY embedding <=> $vetor_da_pergunta
    LIMIT 3;

    Isso é "denormalização intencional" — aceitamos uma pequena
    redundância de dados para garantir performance na operação
    mais crítica do sistema (busca semântica).
    """
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    document_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    # Duplicado de documents.company_id para otimizar a busca RAG
    company_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    agent_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")