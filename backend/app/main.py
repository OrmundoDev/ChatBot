"""
Ponto de entrada da aplicação FastAPI.

O lifespan não cria mais tabelas diretamente.
O schema é responsabilidade exclusiva do Alembic.

Antes de subir o servidor pela primeira vez (ou após uma nova migration):
    alembic upgrade head
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatRequest, ChatResponse
from app.api.dependencies.db import get_db
from app.services.conversation_service import ConversationService
from app.api.webhooks.whatsapp_cloud import router as whatsapp_cloud_router
from app.api.webhooks.evolution import router as evolution_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Nenhuma inicialização de banco aqui.
    # Schema gerenciado pelo Alembic (alembic upgrade head).
    yield


app = FastAPI(
    title="Chatbot - API",
    description="Backend do sistema de atendimento automatizado via WhatsApp",
    version="0.4.0",
    lifespan=lifespan,
)

app.include_router(whatsapp_cloud_router)
app.include_router(evolution_router)


@app.get("/")
def read_root():
    return {
        "mensagem": "API do Chatbot de Imigração está no ar",
        "status": "ok",
        "version": "0.4.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Endpoint de compatibilidade com o n8n atual.
    Usa o agente padrão do banco (primeiro agente ativo encontrado).
    """
    service = ConversationService(db=db)
    resposta = await service.handle_message(
        pergunta=request.pergunta,
        session_id="n8n:default",
        channel_provider="evolution_n8n",
    )
    # Se o bot estiver pausado, retorna string vazia
    # (o n8n não vai enviar nada ao usuário neste caso)
    return ChatResponse(resposta=resposta or "")