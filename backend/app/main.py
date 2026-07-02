from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatRequest, ChatResponse
from app.db.session import engine, Base
from app.api.dependencies.db import get_db
from app.services.conversation_service import ConversationService

# ── Novos routers de webhook ──────────────────────────────────────────────
from app.api.webhooks.whatsapp_cloud import router as whatsapp_cloud_router
from app.api.webhooks.evolution import router as evolution_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Chatbot - API",
    description="Backend do sistema de atendimento automatizado via WhatsApp",
    version="0.4.0",
    lifespan=lifespan,
)

# ── Registro dos routers ──────────────────────────────────────────────────
app.include_router(whatsapp_cloud_router)
app.include_router(evolution_router)


@app.get("/")
def read_root():
    return {"mensagem": "API do Chatbot de Imigração está no ar", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Mantido para compatibilidade com n8n/Evolution API atual."""
    service = ConversationService(db=db)
    resposta = await service.handle_message(
        pergunta=request.pergunta,
        channel_provider="evolution_n8n",  # identifica que veio via n8n
    )
    return ChatResponse(resposta=resposta)