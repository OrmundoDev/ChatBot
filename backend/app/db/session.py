"""
Configuração da conexão com o banco de dados.

Responsabilidade única: criar o engine e a fábrica de sessões.
O Base (schema) fica em base.py.
Os models (tabelas) ficam em models/.
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from app.db.base import Base  # ← vem do base.py, não mais daqui
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    # Verifica se a conexão ainda está viva antes de usar
    pool_pre_ping=True,
)

# Cada requisição HTTP recebe sua própria sessão isolada
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Re-exporta o Base para compatibilidade com imports existentes
__all__ = ["engine", "AsyncSessionLocal", "Base"]