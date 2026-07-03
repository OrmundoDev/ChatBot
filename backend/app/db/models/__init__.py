"""
Ponto central de importação de todos os models.

IMPORTANTE: todo model deve ser importado aqui.
O Alembic importa este arquivo para descobrir todas as tabelas.
Se você criar um model novo e não importar aqui,
o Alembic não enxerga a tabela.
"""

from app.db.models.company import Company
from app.db.models.user import User
from app.db.models.agent import Agent
from app.db.models.channel import Channel
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.document import Document
from app.db.models.chunk import Chunk

__all__ = [
    "Company",
    "User",
    "Agent",
    "Channel",
    "Conversation",
    "Message",
    "Document",
    "Chunk",
]