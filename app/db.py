from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine=create_async_engine(settings.DATABASE_URL,echo=True, pool_size=10, max_overflow=20)

AsyncSessionLocal=sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False)
Base=declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
        