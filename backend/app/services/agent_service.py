"""
AgentService — carrega as configurações de um agente (chatbot).

Responsabilidade única:
Dado um chatbot_id, retorna o AgentConfig com tudo que
o ConversationService precisa saber sobre aquele agente.

AGORA (Etapa 1):
Retorna configurações padrão hardcoded — ainda não há tabela
de chatbots no banco.

ETAPA 2:
AgentService.load() vai fazer SELECT na tabela 'chatbots'
e retornar as configurações salvas para aquele chatbot_id.
Nenhum outro arquivo vai precisar mudar.

ETAPA 5:
Cada chatbot terá seu próprio provider_name e model,
que também virão do banco aqui.
"""

from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# AgentConfig — envelope de dados do agente
#
# Não é um modelo de banco de dados (não herda de Base).
# Não é um schema HTTP (não herda de BaseModel).
# É apenas um "envelope de dados" que trafega entre os serviços internos.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class AgentConfig:
    """
    Configurações completas de um agente/chatbot.

    Todos os campos que o ConversationService precisa para coordenar
    uma resposta estão aqui. Isso evita que os outros serviços precisem
    consultar o banco individualmente.
    """
    system_prompt: str

    # Etapa 5: cada chatbot terá seu próprio provider e modelo
    provider_name: str = "ollama"
    model: str | None = None          # None = usa o padrão do .env
    temperature: float = 0.4

    # Etapa 2 e 3: identificadores para isolar dados por empresa/chatbot
    company_id: str | None = None
    chatbot_id: str | None = None
    name: str = "Assistente"


# ─────────────────────────────────────────────────────────────────────────────
# Prompt padrão — Etapa 2: virá do banco (tabela 'chatbots')
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULT_SYSTEM_PROMPT = (
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


class AgentService:
    """
    Responsável por carregar as configurações de um agente.

    Etapa 1: retorna AgentConfig com valores padrão (hardcoded).
    Etapa 2: vai receber um db: AsyncSession e fazer query na
             tabela 'chatbots' para popular o AgentConfig com
             os dados reais do banco.
    """

    @staticmethod
    async def load(chatbot_id: str | None = None) -> AgentConfig:
        """
        Carrega a configuração do agente solicitado.

        Args:
            chatbot_id: ID do chatbot no banco (Etapa 2).
                        Por enquanto ignorado — só existe um agente padrão.

        Returns:
            AgentConfig com todas as configurações necessárias.
        """
        # ── Etapa 2: substituir este bloco por: ──────────────────────────
        # chatbot = await db.get(Chatbot, chatbot_id)
        # if not chatbot:
        #     raise ValueError(f"Chatbot {chatbot_id} não encontrado")
        # return AgentConfig(
        #     system_prompt=chatbot.system_prompt,
        #     provider_name=chatbot.provider,
        #     model=chatbot.model,
        #     temperature=chatbot.temperature,
        #     company_id=str(chatbot.company_id),
        #     chatbot_id=str(chatbot.id),
        #     name=chatbot.nome,
        # )
        # ─────────────────────────────────────────────────────────────────

        return AgentConfig(
            system_prompt=_DEFAULT_SYSTEM_PROMPT,
            provider_name="ollama",
            temperature=0.4,
            name="Assistente de Imigração",
        )
