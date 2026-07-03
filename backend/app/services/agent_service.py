"""
AgentService — carrega configurações de um agente do banco de dados.

Responsabilidade única:
Dado um agent_id (ou None para o padrão), retorna um AgentConfig
com todas as configurações que o ConversationService precisa.

Etapa 6: o painel administrativo permitirá criar e editar agentes
         sem tocar no código — as mudanças aparecerão aqui automaticamente.
"""

from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.repositories.agent_repository import AgentRepository


@dataclass
class AgentConfig:
    """
    Envelope de dados do agente que trafega entre os serviços.

    Não é um model de banco (não herda de Base).
    Não é um schema HTTP (não herda de BaseModel).
    É um objeto imutável que carrega as configurações
    de um ponto a outro do sistema sem expor o ORM.
    """
    system_prompt: str
    provider_name: str = "ollama"
    model: str | None = None
    temperature: float = 0.4
    company_id: str | None = None
    agent_id: str | None = None
    name: str = "Assistente"


class AgentService:

    @staticmethod
    async def load(
        db: AsyncSession,
        agent_id: UUID | str | None = None,
    ) -> AgentConfig:
        """
        Carrega as configurações do agente do banco de dados.

        Se agent_id for None, retorna o primeiro agente ativo.
        Isso mantém o /chat via n8n funcionando sem precisar
        especificar qual agente deve responder.

         o painel passará o agent_id correto baseado
                 no canal que recebeu a mensagem.
        """
        agent = None

        if agent_id:
            if isinstance(agent_id, str):
                agent_id = UUID(agent_id)
            agent = await AgentRepository.get_by_id(db, agent_id)

        # Fallback: primeiro agente ativo da plataforma
        if agent is None:
            agent = await AgentRepository.get_default(db)

        if agent is None:
            raise RuntimeError(
                "Nenhum agente encontrado no banco. "
                "Execute: alembic upgrade head"
            )

        return AgentConfig(
            system_prompt=agent.system_prompt,
            provider_name=agent.llm_provider,
            model=agent.llm_model,
            temperature=agent.temperature,
            company_id=str(agent.company_id),
            agent_id=str(agent.id),
            name=agent.name,
        )