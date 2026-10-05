# database.py
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

# Строка подключения читается из переменной окружения DATABASE_URL (см. .env.example).
# Формат: postgresql+asyncpg://user:password@host:port/database_name
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL не задана. Скопируйте .env.example в .env "
        "и пропишите строку подключения к PostgreSQL."
    )

# Разрешаем обычный postgresql:// — подставляем драйвер asyncpg.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Асинхронный движок. Таблицы НЕ создаём из ORM «на лету»:
# источник правды по схеме — database/schema.sql.
engine = create_async_engine(DATABASE_URL, echo=False)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Базовый класс для ORM-моделей
class Base(DeclarativeBase):
    pass


# Зависимость (Dependency) для эндпоинтов FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def check_db_connection() -> bool:
    """Пингует БД (SELECT 1). Возвращает True, если PostgreSQL доступна."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
