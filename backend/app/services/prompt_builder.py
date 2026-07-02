"""
PromptBuilder — monta a lista de mensagens para enviar à IA.

Responsabilidade única:
Dado o AgentConfig, o contexto do Knowledge Base, o histórico
da sessão e a pergunta atual, retorna a lista de mensagens
pronta para ser enviada ao LLM Provider.

Não faz I/O (não acessa banco, não chama APIs).
É uma função pura: mesmos inputs → sempre o mesmo output.
Isso facilita muito os testes unitários.
"""

from app.llm.base import ChatMessage
from app.services.agent_service import AgentConfig


class PromptBuilder:
    """
    Constrói a lista de mensagens no formato que os LLM Providers esperam.

    Todos os métodos são estáticos porque o PromptBuilder não tem estado —
    ele só transforma inputs em output. Não precisa ser instanciado.
    """

    @staticmethod
    def build(
        agent_config: AgentConfig,
        context: str,
        history: list[ChatMessage],
        pergunta: str,
    ) -> list[ChatMessage]:
        """
        Monta a lista de mensagens para enviar ao LLM.

        Estrutura final das mensagens:
        [
            {"role": "system",    "content": "<system_prompt do agente>"},
            {"role": "user",      "content": "<mensagem anterior>"},   ← Etapa 4
            {"role": "assistant", "content": "<resposta anterior>"},   ← Etapa 4
            ... (histórico completo da sessão)
            {"role": "user",      "content": "<contexto RAG + pergunta atual>"},
        ]

        Args:
            agent_config: configurações do chatbot (system_prompt, etc.)
            context: texto concatenado dos chunks do Knowledge Base.
                     String vazia se não houver contexto relevante.
            history: mensagens anteriores da sessão (Etapa 4).
                     Lista vazia por enquanto.
            pergunta: texto da mensagem atual do usuário.

        Returns:
            Lista de ChatMessage pronta para provider.generate().
        """
        messages: list[ChatMessage] = []

        # ── 1. System prompt do agente ────────────────────────────────────
        # Define a personalidade, regras e limitações do chatbot.
        # Etapa 2: virá do banco de dados para cada chatbot.
        messages.append({
            "role": "system",
            "content": agent_config.system_prompt,
        })

        # ── 2. Histórico da sessão ────────────────────────────────────────
        # Etapa 4: HistoryService.load() vai popular esta lista.
        # O extend() aqui já está preparado — não vai precisar mudar.
        messages.extend(history)

        # ── 3. Mensagem atual do usuário (com contexto RAG se existir) ────
        if context:
            user_content = (
                f"CONTEXTO (use se for relevante):\n{context}\n\n"
                f"PERGUNTA: {pergunta}"
            )
        else:
            user_content = f"PERGUNTA: {pergunta}"

        messages.append({
            "role": "user",
            "content": user_content,
        })

        return messages

    @staticmethod
    def debug(messages: list[ChatMessage]) -> None:
        """
        Imprime as mensagens formatadas para debug.
        Útil para ver exatamente o que está sendo enviado à IA.

        Uso: PromptBuilder.debug(messages) antes de provider.generate()
        """
        print("\n" + "═" * 60)
        print("  PROMPT MONTADO PARA A IA")
        print("═" * 60)
        for i, msg in enumerate(messages):
            role = msg["role"].upper()
            content = msg["content"]
            # Trunca conteúdos longos para não poluir o terminal
            if len(content) > 300:
                content = content[:300] + "... [truncado]"
            print(f"\n[{i+1}] {role}:\n{content}")
        print("\n" + "═" * 60 + "\n")
