import httpx
from app.core.config import OLLAMA_HOST, OLLAMA_MODEL

SYSTEM_PROMPT = (
    "Você é um assistente virtual que ajuda com diversos assuntos, com "
    "conhecimento especializado em imigração.\n\n"
    "INSTRUÇÕES:\n"
    "1. Quando o CONTEXTO abaixo contiver informação relevante para a "
    "pergunta, use-o como base principal da resposta.\n"
    "2. Quando o CONTEXTO não for relevante para a pergunta, ou estiver "
    "vazio, responda normalmente usando seu próprio conhecimento, como "
    "qualquer assistente de IA faria.\n"
    "3. Nunca mencione a existência de um 'contexto', 'documentos' ou "
    "'base de conhecimento'. Nunca diga frases como 'não encontrei isso' "
    "ou 'baseado nos documentos fornecidos'.\n"
    "4. A resposta deve parecer uma única conversa natural e fluida, "
    "independente de você ter usado o contexto ou seu conhecimento geral."
)


async def perguntar_para_ia(pergunta: str, contexto: str = "") -> str:
    """
    Envia uma pergunta para o Ollama via /api/chat.
    O contexto (quando existir) é oferecido como apoio opcional —
    o modelo decide se usa ou ignora, sem expor isso na resposta.
    """
    if contexto:
        user_content = f"CONTEXTO (use se for relevante):\n{contexto}\n\nPERGUNTA: {pergunta}"
    else:
        user_content = f"PERGUNTA: {pergunta}"

    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "options": {"temperature": 0.4},  # um pouco mais alto que antes: aqui queremos naturalidade, não rigidez
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        resposta = await client.post(url, json=payload)
        resposta.raise_for_status()
        dados = resposta.json()

    return dados["message"]["content"]
