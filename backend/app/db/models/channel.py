from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class Channel(Base):
    """
    Canal de comunicação vinculado a um agente.

    Um agente pode ter múltiplos canais ativos simultaneamente.

    O campo 'config' (JSONB) guarda as credenciais específicas
    de cada provider sem precisar de colunas separadas:

    Evolution API:
        {"api_url": "http://...", "api_key": "xxx", "instance": "nome"}

    WhatsApp Cloud:
        {"access_token": "EAAxx", "phone_number_id": "123", "verify_token": "yyy"}

    'identifier' é o campo usado pelos webhooks para identificar
    qual canal recebeu a mensagem e, consequentemente, qual agente responde:
    - WhatsApp Cloud → phone_number_id
    - Evolution      → nome da instância
    """
    __tablename__ = "channels"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    agent_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    # "evolution" | "whatsapp_cloud" | "telegram" | "instagram" | "webchat"
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    # Credenciais do canal — vêm do banco, nunca do .env em produção
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    agent: Mapped["Agent"] = relationship("Agent", back_populates="channels")
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="channel"
    )