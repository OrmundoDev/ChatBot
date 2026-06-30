from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import DATABASE_URL

# engine = conexão real com o PostgreSQL
engine = create_async_engine(DATABASE_URL, echo=False)

# Fábrica de sessões: cada requisição vai pedir uma sessão nova a partir daqui
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Toda tabela do projeto vai herdar desta Base
Base = declarative_base()
