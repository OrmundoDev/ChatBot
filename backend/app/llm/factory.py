"""
Factory de LLM Providers.

Responsabilidade: dado o nome de um provider como string,
devolver a instância correta já configurada.
"""

from app.llm.base import LLMProvider
from app.llm.providers.ollama_provider import OllamaProvider
from app.llm.providers.openai_provider import OpenAIProvider

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
}


def get_llm_provider(
    provider_name: str = "openai",
    **kwargs,
) -> LLMProvider:
    if provider_name not in _PROVIDERS:
        provedores_disponiveis = list(_PROVIDERS.keys())
        raise ValueError(
            f"Provider '{provider_name}' não reconhecido. "
            f"Disponíveis: {provedores_disponiveis}"
        )
    return _PROVIDERS[provider_name](**kwargs)
