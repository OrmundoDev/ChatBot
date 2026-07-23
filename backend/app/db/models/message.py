from uuid import uuid4
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Message(Base):
    """
    Mensagem individual dentro de uma conversa.

    Cada interação gera duas mensagens separadas:
    - role='user'      → o que o usuário enviou
    - role='assistant' → o que a IA respondeu

    Quando o bot está pausado ('ai_off' ou 'ai_wait'), apenas a
    mensagem do usuário é salva — sem mensagem do assistente.
    Isso permite que o operador humano veja o que o cliente escreveu.

    Ao carregar o histórico, buscamos as N mais recentes no formato:
    [
      {"role": "user",      "content": "Preciso de visto"},
      {"role": "assistant", "content": "Claro, para solicitar..."},
      {"role": "user",      "content": "Pode ser de manhã?"},
    ]
    A IA entende "pode ser de manhã?" sem o usuário repetir o contexto.
    """
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    conversation_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    company_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
