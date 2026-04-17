# main.py
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# postgreSQL
from contextlib import asynccontextmanager
from app.database.session import engine, Base
from app.utils.redis_client import init_redis, close_redis
from app.routers import auth
from app.routers.chat import router as chat_router
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    await init_redis(os.getenv("REDIS_URL"))
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # 关闭时
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="大学生职业规划智能体", 
    version="0.1.0",
    lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 路由挂载
app.include_router(auth.router)
app.include_router(chat_router)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}