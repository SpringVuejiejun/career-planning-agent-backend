import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Optional
import asyncio

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import stream_reply
from app.database.session import get_db, AsyncSessionLocal
from app.dependencies.auth import get_current_user
from app.models.chat import ChatConversation, ChatMessage
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["聊天"])


class ChatMessagePayload(BaseModel):
    role: str = Field(..., description="user | assistant")
    content: str


class ChatStreamRequest(BaseModel):
    messages: list[ChatMessagePayload]
    conversation_id: Optional[int] = None
    title: Optional[str] = None


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None


class ConversationItem(BaseModel):
    id: int
    title: str
    last_message_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ConversationListResponse(BaseModel):
    items: list[ConversationItem]
    total: int


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    key_points: Optional[list[str]] = None
    suggestions: Optional[list[str]] = None
    retrieved_docs: Optional[list[dict[str, Any]]] = None
    seq: int
    created_at: Optional[datetime] = None


def _sse_payload(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _make_title(raw: Optional[str], fallback: str = "新会话") -> str:
    title = (raw or "").strip()
    if not title:
        title = fallback
    return title[:120]


async def _get_conversation_or_404(
    db: AsyncSession,
    conversation_id: int,
    user_id: int,
) -> ChatConversation:
    result = await db.execute(
        select(ChatConversation).where(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user_id,
            ChatConversation.is_deleted.is_(False),
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conversation


async def _next_seq(db: AsyncSession, conversation_id: int) -> int:
    result = await db.execute(
        select(func.max(ChatMessage.seq)).where(ChatMessage.conversation_id == conversation_id)
    )
    current_max = result.scalar()
    return (current_max or 0) + 1


async def save_assistant_message_background(
    conversation_id: int,
    assistant_data: dict,
) -> None:
    """
    后台任务：保存助手消息并更新会话的最后消息时间
    """
    async with AsyncSessionLocal() as db:
        try:
            # 保存助手消息
            assistant_seq = await _next_seq(db, conversation_id)
            db.add(
                ChatMessage(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_data.get("content", ""),
                    key_points=assistant_data.get("key_points"),
                    suggestions=assistant_data.get("suggestions"),
                    retrieved_docs=assistant_data.get("retrieved_docs"),
                    seq=assistant_seq,
                )
            )
            
            # 更新会话的最后消息时间
            result = await db.execute(
                select(ChatConversation).where(ChatConversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                conversation.last_message_at = datetime.utcnow()
                conversation.updated_at = datetime.utcnow()
            
            await db.commit()
            print(f"[后台任务] 成功保存助手消息到会话 {conversation_id}")
        except Exception as e:
            print(f"[后台任务] 保存助手消息失败: {e}")
            await db.rollback()


@router.post("/conversations", response_model=ConversationItem)
async def create_conversation(
    body: CreateConversationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = ChatConversation(
        user_id=current_user.id,
        title=_make_title(body.title),
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return ConversationItem(
        id=conversation.id,
        title=conversation.title,
        last_message_at=conversation.last_message_at,
        created_at=conversation.created_at,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    limit = max(1, min(limit, 100))

    total_result = await db.execute(
        select(func.count(ChatConversation.id)).where(
            ChatConversation.user_id == current_user.id,
            ChatConversation.is_deleted.is_(False),
        )
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(ChatConversation)
        .where(
            ChatConversation.user_id == current_user.id,
            ChatConversation.is_deleted.is_(False),
        )
        .order_by(ChatConversation.last_message_at.desc(), ChatConversation.id.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = result.scalars().all()
    return ConversationListResponse(
        items=[
            ConversationItem(
                id=row.id,
                title=row.title,
                last_message_at=row.last_message_at,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_conversation_or_404(db, conversation_id, current_user.id)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.seq.asc(), ChatMessage.id.asc())
    )
    rows = result.scalars().all()
    return [
        ChatMessageResponse(
            id=row.id,
            role=row.role,
            content=row.content,
            key_points=row.key_points,
            suggestions=row.suggestions,
            retrieved_docs=row.retrieved_docs,
            seq=row.seq,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = await _get_conversation_or_404(db, conversation_id, current_user.id)
    conversation.is_deleted = True
    conversation.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "会话已删除"}


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. 验证请求
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")
    last = body.messages[-1]
    if last.role != "user":
        raise HTTPException(status_code=400, detail="最后一条消息须为用户输入")

    # 2. 获取或创建会话
    if body.conversation_id:
        conversation = await _get_conversation_or_404(db, body.conversation_id, current_user.id)
        await db.refresh(conversation)
    else:
        conversation = ChatConversation(
            user_id=current_user.id,
            title=_make_title(body.title, fallback=last.content[:30] or "新会话"),
        )
        db.add(conversation)
        await db.flush()
        await db.refresh(conversation)

    # 3. 保存用户消息
    user_seq = await _next_seq(db, conversation.id)
    db.add(
        ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content=last.content,
            seq=user_seq,
        )
    )
    conversation.last_message_at = datetime.utcnow()
    conversation.updated_at = datetime.utcnow()
    await db.commit()
    
    # 刷新会话对象，确保所有属性都已加载
    await db.refresh(conversation)

    # 4. 准备历史消息和会话ID
    history = [m.model_dump() for m in body.messages]
    conversation_id = conversation.id
    
    # 5. 创建队列用于流式传输
    chunk_queue = asyncio.Queue()
    
    # 6. 定义异步生成器函数来收集流式结果
    async def collect_stream_result():
        """收集流式响应的完整结果"""
        full_content = ""
        key_points = None
        suggestions = None
        retrieved_docs = None
        
        try:
            async for chunk in stream_reply(history):
                if isinstance(chunk, dict):
                    # 如果是回复块，累积内容
                    if chunk.get("type") == "reply":
                        full_content = chunk.get("content", "")
                        key_points = chunk.get("key_points")
                        suggestions = chunk.get("suggestions")
                        retrieved_docs = chunk.get("retrieved_docs")
                    
                    # 将块放入队列用于实时传输
                    await chunk_queue.put(("chunk", chunk))
                else:
                    # 处理非字典类型的块
                    await chunk_queue.put(("chunk", {"type": "text", "content": str(chunk)}))
            
            # 所有块处理完毕，将完整结果放入队列
            await chunk_queue.put(("result", {
                "content": full_content,
                "key_points": key_points,
                "suggestions": suggestions,
                "retrieved_docs": retrieved_docs
            }))
            
        except Exception as e:
            # 发生错误时，将错误信息放入队列
            await chunk_queue.put(("error", str(e)))
    
    # 7. 定义SSE流响应生成器
    async def sse_stream() -> AsyncIterator[str]:
        # 启动后台收集任务
        collect_task = asyncio.create_task(collect_stream_result())
        
        try:
            while True:
                try:
                    # 从队列获取数据，超时设置为30秒
                    item_type, item_data = await asyncio.wait_for(chunk_queue.get(), timeout=30.0)
                    
                    if item_type == "chunk":
                        # 实时发送流式块
                        if isinstance(item_data, dict):
                            # 添加会话ID到每个块
                            item_data["conversation_id"] = conversation_id
                            yield _sse_payload(item_data)
                        else:
                            yield _sse_payload({"type": "text", "content": str(item_data)})
                    
                    elif item_type == "result":
                        # 收到完整结果，添加到后台任务保存到数据库
                        background_tasks.add_task(
                            save_assistant_message_background,
                            conversation_id,
                            item_data
                        )
                        break
                    
                    elif item_type == "error":
                        # 发送错误信息
                        yield _sse_payload({
                            "type": "error", 
                            "content": f"服务异常: {item_data}", 
                            "is_final": True
                        })
                        break
                        
                except asyncio.TimeoutError:
                    # 超时处理
                    yield _sse_payload({
                        "type": "error", 
                        "content": "响应超时", 
                        "is_final": True
                    })
                    break
        
        finally:
            # 清理任务
            collect_task.cancel()
            try:
                await collect_task
            except asyncio.CancelledError:
                pass
            
            # 发送结束标记
            yield _sse_payload({"type": "end", "is_final": True, "conversation_id": conversation_id})
            yield "data: [DONE]\n\n"
    
    # 8. 返回流式响应
    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
        },
    )