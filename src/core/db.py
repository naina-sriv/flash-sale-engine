from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.core.config import DATABASE_URL

if "sqlite" in DATABASE_URL:
    engine = create_async_engine(DATABASE_URL, echo=True)
else:
    engine = create_async_engine(DATABASE_URL, echo=True, pool_size=10, max_overflow=20)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
