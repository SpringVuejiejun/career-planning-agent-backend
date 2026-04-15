# session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database.base import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL")

# 创建引擎
engine = create_async_engine(DATABASE_URL, echo=False)

# 会话工厂
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)

# 依赖函数
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()