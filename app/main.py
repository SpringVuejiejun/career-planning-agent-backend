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


def _sse_payload(text: str) -> str:
    return f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"


async def sse_stream(history: list[dict[str, str]]) -> AsyncIterator[str]:
    try:
        async for piece in stream_reply(history):
            yield _sse_payload(piece)
    except RuntimeError as e:
        yield _sse_payload(f"\n\n[配置错误] {e}")
    except Exception as e:  # noqa: BLE001
        yield _sse_payload(f"\n\n[服务异常] {e!s}")
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
