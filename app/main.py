# main.py
import json
from collections.abc import AsyncIterator
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent import stream_reply

app = FastAPI(title="大学生职业规划智能体", version="0.1.0")

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


class ChatMessage(BaseModel):
    role: str = Field(..., description="user | assistant")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _sse_payload(data: dict) -> str:
    """发送结构化数据而不是纯文本"""
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


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat/stream")
async def chat_stream(body: ChatRequest):
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")
    last = body.messages[-1]
    if last.role != "user":
        raise HTTPException(status_code=400, detail="最后一条消息须为用户输入")
    history = [m.model_dump() for m in body.messages]
    return StreamingResponse(
        sse_stream(history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )