from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Document(Base):
    """
    Arquivo enviado para o Knowledge Base de uma empresa.

    Vinculado obrigatoriamente à empresa (company_id) —
    nenhuma empresa acessa documentos de outra.

    agent_id é opcional:
    - NULL     → documento compartilhado por todos os agentes da empresa
    - UUID     → documento exclusivo daquele agente
    """
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    company_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    agent_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    company: Mapped["Company"] = relationship("Company")
    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="document")