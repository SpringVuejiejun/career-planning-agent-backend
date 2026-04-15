# main.py
import json
from collections.abc import AsyncIterator
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent import stream_reply

# postgreSQL
from contextlib import asynccontextmanager
from app.database.session import engine, Base
from app.utils.redis_client import init_redis, close_redis
from app.routers import auth
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


class ChatMessage(BaseModel):
    role: str = Field(..., description="user | assistant")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _sse_payload(data: dict) -> str:
    # 返回以data: 开头的结构化数据
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def sse_stream(history: list[dict[str, str]]) -> AsyncIterator[str]:
    try:
        async for chunk in stream_reply(history):
            # chunk 现在是字典对象，直接发送
            if isinstance(chunk, dict):
                yield _sse_payload(chunk)
            else:
                # 兼容性处理
                yield _sse_payload({"type": "text", "content": str(chunk)})
    except RuntimeError as e:
        yield _sse_payload({"type": "error", "content": f"配置错误: {e}", "is_final": True})
    except Exception as e:
        yield _sse_payload({"type": "error", "content": f"服务异常: {e!s}", "is_final": True})
    
    # 发送结束标记
    yield _sse_payload({"type": "end", "is_final": True})
    yield "data: [DONE]\n\n"


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/chat/stream")
async def chat_stream(body: ChatRequest):
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")
    last = body.messages[-1]
    if last.role != "user":
        raise HTTPException(status_code=400, detail="最后一条消息须为用户输入")
    # 此时收到的消息是chatMessage类型，需要使用pydantic的model_dump方法转换成字典列表
    history = [m.model_dump() for m in body.messages]
    # 开始流式输出返回响应
    return StreamingResponse(
        # 调用sse_stream生成器函数，生成规范的SSE事件流
        sse_stream(history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )