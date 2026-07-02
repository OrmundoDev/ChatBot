"""
Implementação do LLMProvider para o Ollama.

Responsabilidade única deste arquivo:
Saber como falar com a API do Ollama. Nada mais.

Ele não sabe nada sobre RAG, contexto, prompts do sistema,
banco de dados ou regras de negócio. Recebe uma lista de mensagens
já montada, envia para o Ollama e devolve o texto da resposta.
"""

import httpx
from app.core.config import OLLAMA_HOST, OLLAMA_MODEL
from app.llm.base import LLMProvider, ChatMessage


class OllamaProvider(LLMProvider):
    """
    Provedor de LLM que se comunica com uma instância local do Ollama.

    O modelo e o host são configuráveis via construtor, mas têm valores
    padrão vindos do .env — assim o código funciona sem precisar passar
    nada, mas também pode ser sobrescrito por chatbot na Etapa 5.
    """

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
    ):
        # Se não informar, usa o que está no .env (OLLAMA_MODEL e OLLAMA_HOST).
        # Na Etapa 5, cada chatbot no banco de dados vai passar seu próprio
        # model e host aqui, sem alterar nenhum outro arquivo.
        self.model = model or OLLAMA_MODEL
        self.host = host or OLLAMA_HOST

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.4,
    ) -> str:
        """
        Envia a lista de mensagens para o Ollama e retorna o texto gerado.

        O formato da lista é o mesmo que o Ollama já espera nativamente:
        [
            {"role": "system", "content": "..."},
            {"role": "user",   "content": "..."},
            {"role": "assistant", "content": "..."},  ← histórico futuro (Etapa 4)
            {"role": "user",   "content": "..."},
        ]

        Na Etapa 4 (memória de conversa), o ConversationService vai popular
        esse mesmo messages[] com o histórico da sessão — este método não
        precisa mudar nada para suportar isso.
        """
        url = f"{self.host}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,       # já vem montado pelo ConversationService
            "stream": False,
            "keep_alive": "30m",
            "options": {"temperature": temperature},
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            resposta = await client.post(url, json=payload)
            resposta.raise_for_status()
            dados = resposta.json()

        # Extrai só o texto — quem chamou não precisa saber da estrutura
        # JSON interna do Ollama.
        return dados["message"]["content"]
