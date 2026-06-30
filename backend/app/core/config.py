import os
from pathlib import Path
from dotenv import load_dotenv

# app/core/config.py está 4 níveis abaixo da raiz do projeto:
# config.py -> core/ -> app/ -> backend/ -> chatbot-imigracao/ (raiz)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Configurações do Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")

# Configurações do PostgreSQL
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
