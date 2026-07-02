"""
Camada de abstração de canais de comunicação.

Responsabilidade:
Define o contrato que todo canal deve seguir e o formato
padrão de mensagem que trafega dentro do sistema.

Por que existe:
O ConversationService não deve saber se a mensagem veio do
WhatsApp, Telegram, Instagram ou de uma API direta. Assim
como o LLM Provider abstrai qual IA está respondendo, o
Channel Provider abstrai de onde a mensagem veio e para
onde a resposta deve ir.

Canais suportados agora:   evolution, whatsapp_cloud
Canais planejados (stubs): telegram, instagram, webchat
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class IncomingMessage:
    """
    Formato padrão de mensagem recebida, independente do canal.

    Qualquer canal (Evolution, WhatsApp Cloud, Telegram...)
    precisa transformar seu payload nativo neste formato antes
    de passar para o ConversationService. Isso garante que o
    ConversationService só conhece este formato único.
    """
    # De qual canal veio (ex: "evolution", "whatsapp_cloud")
    channel_provider: str

    # ID do remetente no canal (número de telefone, user_id, etc.)
    from_id: str

    # ID do destinatário (o número/instância do bot)
    to_id: str

    # ID único da mensagem no canal (usado para deduplicação)
    message_id: str

    # Texto da mensagem
    content: str

    # ID da sessão de conversa — por padrão é o from_id
    # Etapa 4: será usado para buscar o histórico da sessão
    session_id: str = field(default="")

    # Qual chatbot/agente deve responder
    # Etapa 2: virá do banco baseado em qual canal recebeu a mensagem
    chatbot_id: str | None = None

    # Payload original do canal (para debug e auditoria)
    raw: dict = field(default_factory=dict)

    def __post_init__(self):
        # Se session_id não for informado, usa o from_id como identificador
        # da sessão (cada número de telefone = uma conversa separada)
        if not self.session_id:
            self.session_id = f"{self.channel_provider}:{self.from_id}"


@dataclass
class OutgoingMessage:
    """
    Formato padrão de mensagem a ser enviada, independente do canal.
    """
    to_id: str       # destinatário (número de telefone, user_id, etc.)
    content: str     # texto da resposta
    channel_provider: str   # qual canal usar para enviar


class ChannelProvider(ABC):
    """
    Contrato que todo provedor de canal deve implementar.

    Cada canal concreto (Evolution, WhatsApp Cloud, Telegram...)
    implementa esta interface. O resto do sistema só conhece
    estes três métodos — nunca os detalhes de cada API.
    """

    @abstractmethod
    async def parse_incoming(self, payload: dict) -> IncomingMessage | None:
        """
        Transforma o payload nativo do canal em IncomingMessage.

        Retorna None se a mensagem deve ser ignorada
        (ex: mensagem do próprio bot, notificação de status,
        mensagem de mídia sem texto, etc.)

        Args:
            payload: JSON recebido no webhook do canal.

        Returns:
            IncomingMessage normalizado, ou None para ignorar.
        """
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, to_id: str, content: str) -> bool:
        """
        Envia uma mensagem de resposta ao usuário pelo canal.

        Args:
            to_id: identificador do destinatário neste canal.
            content: texto da resposta a enviar.

        Returns:
            True se enviou com sucesso, False caso contrário.
        """
        raise NotImplementedError

    @abstractmethod
    async def verify_webhook(self, params: dict) -> str | None:
        """
        Verifica a autenticidade do webhook (se o canal exigir).

        Usado principalmente pelo WhatsApp Cloud API, que envia
        um GET com hub.challenge antes de começar a enviar mensagens.

        Args:
            params: query parameters do request de verificação.

        Returns:
            String a retornar ao canal (ex: hub.challenge),
            ou None se não houver verificação necessária.
        """
        raise NotImplementedError