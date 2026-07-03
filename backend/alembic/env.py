"""
Configuração do Alembic para SQLAlchemy assíncrono.

Executado toda vez que você roda 'alembic upgrade head'
ou 'alembic revision --autogenerate'.

O que ele faz:
1. Importa todos os models para o Alembic "ver" as tabelas
2. Usa as settings do projeto para a URL do banco (sem hardcode)
3. Executa migrações de forma assíncrona (mesmo driver do app)
"""

import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from alembic import context

# Configurações do projeto
from app.core.config import settings

# OBRIGATÓRIO: importar o Base e TODOS os models
# Se um model não for importado aqui, o Alembic não detecta a tabela
from app.db.base import Base
import app.db.models  # noqa: F401 — efeito colateral: registra todos os models

target_metadata = Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Sobrescreve o placeholder com a URL real — nunca hardcode aqui
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """Modo offline: gera SQL sem conectar no banco."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()