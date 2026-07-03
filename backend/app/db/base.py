"""
Base declarativa do SQLAlchemy.

Arquivo exclusivo para o Base — sem engine, sem sessão, sem imports do projeto.

Por que existe separado:
O Alembic precisa importar o Base para descobrir as tabelas sem
inicializar o engine. Se o Base estivesse dentro do session.py,
importá-lo tentaria conectar no banco — o que quebra as migrações.

Regra: nenhum outro import deve entrar neste arquivo.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Classe raiz de todos os models do projeto.

    Todo model herda desta classe. Isso faz o SQLAlchemy
    registrar automaticamente a tabela no Base.metadata,
    que é o "mapa" que o Alembic usa para descobrir o schema.
    """
    pass
