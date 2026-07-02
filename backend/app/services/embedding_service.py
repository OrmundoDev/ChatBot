import httpx
from app.core.config import OLLAMA_HOST, EMBEDDING_MODEL


async def gerar_embedding(texto: str) -> list[float]:
    """
    Envia um texto para o Ollama e retorna seu vetor de embedding (1024 posições).
    """
    url = f"{OLLAMA_HOST}/api/embed"

    payload = {
        "model": EMBEDDING_MODEL,
        "input": texto,
        "keep_alive": "30m"
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resposta = await client.post(url, json=payload)
        resposta.raise_for_status()
        dados = resposta.json()

    return dados["embeddings"][0]
