"""
Configurações centrais da aplicação.

Usa Pydantic BaseSettings para:
1. Ler variáveis do arquivo .env automaticamente
2. Validar tipos na inicialização do servidor
3. Disponibilizar um objeto 'settings' único para todo o sistema

Se uma variável obrigatória estiver faltando no .env, o servidor
não sobe e mostra exatamente qual variável está faltando.
Isso evita falhas silenciosas em produção.

Hierarquia de configuração:
.env → BaseSettings → objeto settings → importado pelos módulos
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Localização do .env: 4 níveis acima deste arquivo
# config.py → core/ → app/ → backend/ → chatbot-imigracao/ (raiz)
_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """
    Todas as configurações da aplicação em um único lugar.

    Campos sem valor padrão (ex: POSTGRES_USER) são OBRIGATÓRIOS —
    o servidor não sobe se não encontrá-los no .env.

    Campos com valor padrão (ex: OLLAMA_HOST) são opcionais —
    o servidor usa o padrão se não encontrá-los.

    Campos com padrão None são opcionais e não ativados por padrão
    (ex: credenciais do WhatsApp Cloud que o cliente nem sempre usa).
    """

    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        # Ignora variáveis extras no .env que não estão declaradas aqui
        extra="ignore",
    )

    # ── Ollama ────────────────────────────────────────────────────────────
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:3b"
    EMBEDDING_MODEL: str = "bge-m3"

    # ── PostgreSQL ────────────────────────────────────────────────────────
    # Sem padrão = obrigatório no .env
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432          # já converte string para int automaticamente

    # ── Evolution API ─────────────────────────────────────────────────────
    # Usada tanto pelo modo n8n (atual) quanto pelo webhook direto (novo).
    # Opcionais: se não configuradas, o webhook direto da Evolution
    # vai logar um aviso mas o /chat via n8n continua funcionando.
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE: str = ""

    # ── WhatsApp Cloud API (Meta) ─────────────────────────────────────────
    # Necessário apenas para clientes que usam a API oficial.
    # None = não configurado = provider não funcional (mas não quebra o servidor)
    WHATSAPP_CLOUD_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_CLOUD_ACCESS_TOKEN: str | None = None
    WHATSAPP_CLOUD_VERIFY_TOKEN: str | None = None

    # ── Canais futuros (stubs) ────────────────────────────────────────────
    # Adicionar aqui quando implementar cada canal
    # TELEGRAM_BOT_TOKEN: str | None = None
    # INSTAGRAM_ACCESS_TOKEN: str | None = None

    @property
    def DATABASE_URL(self) -> str:
        """
        Monta a URL de conexão do banco dinamicamente a partir das partes.

        Usando asyncpg como driver assíncrono (exigido pelo SQLAlchemy async).
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


# ── Instância única (singleton) ───────────────────────────────────────────
#
# Todo o sistema importa ESTE objeto, nunca cria um novo Settings().
# Isso garante que as variáveis são lidas do disco uma única vez.
#
settings = Settings()


# ── Aliases de compatibilidade ────────────────────────────────────────────
#
# Mantidos para que ollama_service.py, embedding_service.py e outros
# arquivos que importam variáveis soltas continuem funcionando SEM
# precisar de alteração agora.
#
# Na Etapa 2 (refatoração do banco), removeremos estes aliases e
# atualizaremos os imports diretamente para `settings.VARIAVEL`.
#
OLLAMA_HOST = settings.OLLAMA_HOST
OLLAMA_MODEL = settings.OLLAMA_MODEL
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
DATABASE_URL = settings.DATABASE_URL