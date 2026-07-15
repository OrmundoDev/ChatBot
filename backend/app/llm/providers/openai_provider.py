"""
Implementação do LLMProvider para a OpenAI.

Responsabilidade única deste arquivo:
Saber como falar com a API da OpenAI. Nada mais.
"""

from openai import AsyncOpenAI
from app.core.config import settings
from app.llm.base import LLMProvider, ChatMessage


class OpenAIProvider(LLMProvider):
    """
    Provedor de LLM que se comunica com a API da OpenAI.
    """

    def __init__(self, model: str | None = None):
        self.model = model or "gpt-5.4-mini"
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.4,
    ) -> str:
        resposta = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return resposta.choices[0].message.content
