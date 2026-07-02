"""
Factory de Channel Providers.

Mesmo padrão do LLMFactory: dado o nome do canal como string,
devolve a instância correta do provider já configurada.

Adicionar um novo canal = adicionar uma linha em _CHANNELS.
O resto do sistema não precisa mudar.
"""

from app.channels.base import ChannelProvider


def get_channel_provider(provider_name: str, config: dict | None = None) -> ChannelProvider:
    """
    Retorna o provider de canal solicitado.

    Args:
        provider_name: nome do canal ("evolution", "whatsapp_cloud", etc.)
        config: configurações específicas do canal.
                Etapa 2: virá do campo config (JSON) da tabela channels.
                Por agora: virá do .env ou de um dict hardcoded.

    Raises:
        ValueError: se o provider_name não for reconhecido.
    """
    # Import local para evitar importações circulares e carregar
    # só o provider que for de fato usado
    from app.channels.providers.evolution_provider import EvolutionProvider
    from app.channels.providers.whatsapp_cloud_provider import WhatsAppCloudProvider
    from app.channels.providers.telegram_provider import TelegramProvider
    from app.channels.providers.instagram_provider import InstagramProvider
    from app.channels.providers.webchat_provider import WebChatProvider

    _CHANNELS: dict[str, type[ChannelProvider]] = {
        "evolution":       EvolutionProvider,
        "whatsapp_cloud":  WhatsAppCloudProvider,
        "telegram":        TelegramProvider,    # stub
        "instagram":       InstagramProvider,   # stub
        "webchat":         WebChatProvider,     # stub
    }

    if provider_name not in _CHANNELS:
        disponiveis = list(_CHANNELS.keys())
        raise ValueError(
            f"Canal '{provider_name}' não reconhecido. "
            f"Disponíveis: {disponiveis}"
        )

    config = config or {}
    return _CHANNELS[provider_name](config=config)