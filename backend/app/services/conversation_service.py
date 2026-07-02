"""
ConversationService — coordenador do fluxo de conversa.

Responsabilidade única:
Orquestrar os serviços especializados em ordem correta
para transformar uma mensagem do usuário em uma resposta da IA.

Este arquivo NÃO deve conter:
- Lógica de busca de embeddings (→ KnowledgeService)
- Lógica de construção de prompts (→ PromptBuilder)
- Lógica de histórico de conversa (→ HistoryService)
- Lógica de configuração de agentes (→ AgentService)
- Comunicação com APIs de IA (→ LLMProvider)

Se alguma dessas coisas precisar mudar, este arquivo
não deve ser tocado.
"""

import time
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_service import AgentService
from app.services.knowledge_service import KnowledgeService
from app.services.history_service import HistoryService
from app.services.prompt_builder import PromptBuilder
from app.llm.factory import get_llm_provider


class ConversationService:
    """
    Coordena o fluxo completo de uma mensagem até a resposta.

    A sessão de banco é injetada aqui e repassada para os
    serviços que precisam de I/O (KnowledgeService, HistoryService).
    AgentService e PromptBuilder não precisam de banco.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def handle_message(
        self,
        pergunta: str,
        chatbot_id: str | None = None,   # Etapa 2: identificar qual chatbot
        session_id: str | None = None,   # Etapa 4: identificar a sessão
        channel_provider: str | None = None,
   ) -> str:
        """
        Processa uma mensagem e retorna a resposta da IA.

        Args:
            pergunta: texto enviado pelo usuário.
            chatbot_id: qual chatbot/agente deve responder.
                        Etapa 2: cada empresa terá seu próprio chatbot_id.
            session_id: qual sessão de conversa está ativa.
                        Etapa 4: permite carregar o histórico correto.

        Returns:
            Texto da resposta gerada pela IA.
        """
        inicio = time.perf_counter()
        # Log de contexto - util para rastrear de qual canal veio a mensagem
        if channel_provider:
            print(f"[ConversationService] Canal: {channel_provider} | Sessão: {session_id}")
        # ── 1. Carregar configurações do agente ───────────────────────────
        # "Quem vai responder? Com qual personalidade e modelo?"
        agente = await AgentService.load(chatbot_id)

        # ── 2. Buscar contexto no Knowledge Base ──────────────────────────
        # "O que os documentos da empresa sabem sobre isso?"
        knowledge = KnowledgeService(self.db)
        contexto = await knowledge.search(pergunta, agente.company_id)

        # ── 3. Carregar histórico da sessão ───────────────────────────────
        # "O que foi dito antes nesta conversa?"
        history_svc = HistoryService(self.db)
        historico = await history_svc.load(session_id)

        # ── 4. Montar o pacote de mensagens para a IA ─────────────────────
        # "Como empacotar tudo isso para o modelo entender?"
        messages = PromptBuilder.build(agente, contexto, historico, pergunta)

        # Descomente para ver o prompt completo no terminal durante debug:
        # PromptBuilder.debug(messages)

        # ── 5. Obter o provider e gerar a resposta ────────────────────────
        # "Qual IA usar? Qual modelo? Qual temperatura?"
        provider = get_llm_provider(agente.provider_name, model=agente.model)
        resposta = await provider.generate(messages, temperature=agente.temperature)

        # ── 6. Salvar a interação no banco ────────────────────────────────
        # "Registrar o que aconteceu para histórico e métricas."
        await history_svc.save(session_id, pergunta, resposta)

        print(f"[ConversationService][TEMPO] TOTAL: {time.perf_counter() - inicio:.2f}s")

        return resposta