from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Conversation(Base):
    """
    Sessão de conversa entre um usuário e um agente.

    Criada na primeira mensagem e reutilizada em todas as
    mensagens seguintes do mesmo usuário no mesmo canal.

    'session_id' é a chave de busca — formato "provider:identificador":
    - "whatsapp_cloud:5511999999999"
    - "evolution:5511888888888"

    'status' controla se o bot responde ou não:
    - 'ai_active'    → bot responde normalmente (padrão)
    - 'human_active' → humano está atendendo, bot não responde
    - 'waiting_human'→ bot pediu intervenção humana

    Esta abordagem com VARCHAR permite evoluir para novos estados
    sem alterar o schema do banco no futuro.
    """
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    agent_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    channel_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id"), nullable=True
    )
    session_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    from_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Estados possíveis: 'ai_active' | 'human_active' | 'waiting_human'
    status: Mapped[str] = mapped_column(String(30), default="ai_active")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    agent: Mapped["Agent"] = relationship("Agent", back_populates="conversations")
    channel: Mapped["Channel"] = relationship(
        "Channel", back_populates="conversations"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        order_by="Message.created_at",
    )