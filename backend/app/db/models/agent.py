from uuid import uuid4
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Agent(Base):
    """
    Agente de IA configurável — o coração da plataforma.

    Cada empresa pode ter múltiplos agentes com personalidades,
    modelos e comportamentos completamente diferentes.

    Exemplos:
    - Agente "Triagem"     → ollama, qwen3b, temp 0.2, prompt formal
    - Agente "Consultoria" → openai, gpt-4o, temp 0.7, prompt consultivo
    - Agente "Suporte"     → anthropic, claude, temp 0.3, prompt técnico

    O system_prompt define quem o agente é e como se comporta.
    Configurável pelo painel sem tocar no código.
    """
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    company_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Configurações do modelo de linguagem
    llm_provider: Mapped[str] = mapped_column(String(50), default="ollama")
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.4)

    # Personalidade e regras do agente — editável no painel, sem deploy
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company"] = relationship("Company", back_populates="agents")
    channels: Mapped[list["Channel"]] = relationship(
        "Channel", back_populates="agent"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="agent"
    )