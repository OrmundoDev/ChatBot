from openai import AsyncOpenAI
from app.core.config import settings

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def gerar_embedding(texto: str) -> list[float]:
    """
    Envia um texto para a OpenAI e retorna seu vetor de embedding
    (1536 posições, modelo text-embedding-3-small).
    """
    resposta = await _client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texto,
    )
    return resposta.data[0].embedding
