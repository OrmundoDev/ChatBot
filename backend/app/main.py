from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatRequest, ChatResponse
from app.services.ollama_service import perguntar_para_ia
from app.services.embedding_service import gerar_embedding
from app.db.session import engine, Base
from app.db.models import Conversa, DocumentoChunk
from app.api.dependencies.db import get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # Garante que a extensão pgvector está habilitada antes de criar tabelas
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Chatbot de Imigração - API",
    description="Backend do sistema de atendimento automatizado via WhatsApp",
    version="0.2.0",
    lifespan=lifespan
)


@app.get("/")
def read_root():
    return {
        "mensagem": "API do Chatbot de Imigração está no ar",
        "status": "ok"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    try:
        # 1. Gera o embedding da pergunta do usuário
        embedding_pergunta = await gerar_embedding(request.pergunta)

        # 2. Busca os 3 chunks de documentos mais relevantes
        resultado = await db.execute(
            select(DocumentoChunk)
            .order_by(DocumentoChunk.embedding.cosine_distance(embedding_pergunta))
            .limit(3)
        )
        chunks_relevantes = resultado.scalars().all()
        contexto = "\n\n---\n\n".join(c.conteudo for c in chunks_relevantes)

        # 3. Pergunta à IA, agora com o contexto encontrado
        resposta = await perguntar_para_ia(request.pergunta, contexto)
    except Exception as erro:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao se comunicar com o modelo de IA: {erro}"
        )

    nova_conversa = Conversa(pergunta=request.pergunta, resposta=resposta)
    db.add(nova_conversa)
    await db.commit()

    return ChatResponse(resposta=resposta)
