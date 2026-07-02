"""
Contrato (interface) que todo provedor de LLM deve seguir.

Por que isso existe:
O resto do sistema (Conversation Service, rotas) nunca deve saber
se está conversando com Ollama, OpenAI, Anthropic ou qualquer outro
modelo. Ele só conhece este contrato. Trocar de provedor = criar uma
nova classe que implementa esta interface, sem tocar em mais nada
no resto da aplicação.
"""

from abc import ABC, abstractmethod
from typing import TypedDict


class ChatMessage(TypedDict):
    """
    Formato padrão de uma mensagem dentro da conversa.

    role: 'system' (instrução do chatbot), 'user' (pergunta do
          usuário) ou 'assistant' (resposta anterior da IA).
    content: o texto da mensagem.
    """
    role: str
    content: str


class LLMProvider(ABC):
    """
    Interface base para qualquer provedor de modelo de linguagem.

    Toda classe concreta (OllamaProvider, OpenAIProvider,
    AnthropicProvider...) precisa implementar o método generate()
    com esta mesma assinatura. É isso que permite ao
    ConversationService chamar qualquer provider sem saber
    qual é, de fato, por baixo dos panos.
    """

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> str:
        """
        Recebe o histórico de mensagens (já incluindo o contexto
        do RAG, se houver) e devolve o texto da resposta gerada.

        Toda implementação concreta precisa devolver sempre uma
        string simples aqui, mesmo que a API externa retorne um
        JSON complexo por baixo — quem chama generate() não quer
        saber desses detalhes.
        """
        raise NotImplementedError