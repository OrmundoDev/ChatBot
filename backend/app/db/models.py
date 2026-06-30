from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.session import Base


class Conversa(Base):
    __tablename__ = "conversas"

    id = Column(Integer, primary_key=True, index=True)
    pergunta = Column(Text, nullable=False)
    resposta = Column(Text, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())


class DocumentoChunk(Base):
    __tablename__ = "documentos_chunks"

    id = Column(Integer, primary_key=True, index=True)
    nome_arquivo = Column(Text, nullable=False)
    conteudo = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
