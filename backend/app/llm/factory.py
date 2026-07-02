"""
Factory de LLM Providers.

Responsabilidade: dado o nome de um provider como string,
devolver a instância correta já configurada.

Benefício: o ConversationService nunca precisa importar
OllamaProvider, OpenAIProvider, etc. diretamente. Ele só
conhece o factory — e o factory conhece todos os providers.
Adicionar um novo provider = adicionar uma linha no dicionário
'_PROVIDERS' abaixo. Nada mais muda no resto do sistema.
"""

from app.llm.base import LLMProvider
from app.llm.providers.ollama_provider import OllamaProvider

# Registro de todos os providers disponíveis.
# Etapa 5: adicionar entradas aqui para OpenAI, Anthropic, Gemini, etc.
_PROVIDERS: dict[str, type[LLMProvider]] = {
    "ollama": OllamaProvider,
}


def get_llm_provider(
    provider_name: str = "ollama",
    **kwargs,
) -> LLMProvider:
    """
    Retorna uma instância do provider solicitado.

    Args:
        provider_name: nome do provider (ex: "ollama", "openai").
        **kwargs: parâmetros opcionais repassados ao construtor do provider
                  (ex: model="gpt-4", host="http://...").
                   as configurações do chatbot no banco virão aqui.

    Raises:
        ValueError: se o provider_name não estiver registrado.
    """
    if provider_name not in _PROVIDERS:
        provedores_disponiveis = list(_PROVIDERS.keys())
        raise ValueError(
            f"Provider '{provider_name}' não reconhecido. "
            f"Disponíveis: {provedores_disponiveis}"
        )

    # Instancia e devolve — os kwargs permitem personalização por chatbot
    return _PROVIDERS[provider_name](**kwargs)
