from uuid import uuid4
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Company(Base):
    """
    Representa uma empresa cliente da plataforma.

    'slug' é um identificador único em formato URL-friendly:
    ex: "escritorio-silva", "imigra-facil".
    Usado internamente para identificar a empresa sem expor o UUID.
    """
    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos — permitem acessar agents e users direto pelo objeto
    agents: Mapped[list["Agent"]] = relationship("Agent", back_populates="company")
    users: Mapped[list["User"]] = relationship("User", back_populates="company")