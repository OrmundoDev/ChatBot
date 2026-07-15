"""
Configurações centrais da aplicação.

Usa Pydantic BaseSettings para:
1. Ler variáveis do arquivo .env automaticamente
2. Validar tipos na inicialização do servidor
3. Disponibilizar um objeto 'settings' único para todo o sistema

Se uma variável obrigatória estiver faltando no .env, o servidor
não sobe e mostra exatamente qual variável está faltando.
Isso evita falhas silenciosas em produção.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── OpenAI ──────────────────────────────────────────────
    OPENAI_API_KEY: str

    # ── Ollama (mantido para uso futuro / servidor de IA local) ──
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:3b"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ── PostgreSQL ──────────────────────────────────────────
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432

    # ── Evolution API ───────────────────────────────────────
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE: str = ""

    # ── WhatsApp Cloud API (Meta) ───────────────────────────
    WHATSAPP_CLOUD_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_CLOUD_ACCESS_TOKEN: str | None = None
    WHATSAPP_CLOUD_VERIFY_TOKEN: str | None = None

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()

OLLAMA_HOST = settings.OLLAMA_HOST
OLLAMA_MODEL = settings.OLLAMA_MODEL
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
DATABASE_URL = settings.DATABASE_URL
