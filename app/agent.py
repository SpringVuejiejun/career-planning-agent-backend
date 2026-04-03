from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_base_url, get_model_name, get_openai_api_key

SYSTEM_PROMPT = """你是一位专注服务中国大学生的职业规划顾问智能体。你的目标是帮助学生澄清职业方向、制定可执行的路径，并在求职与学业之间做出平衡。

原则：
- 语气友好、专业、具体；避免空泛鸡汤。
- 先理解学生的专业背景、年级、兴趣与约束（城市、家庭、经济等），再给出建议。
- 需要更多信息时，用 1–3 个简短问题追问，而不是一次问太多。
- 涉及薪资、行业前景时说明这是粗略区间且因地区与时间变化，建议结合官方数据与校招信息核实。
- 不代替正式心理咨询；若用户表现出严重心理危机倾向，应建议联系学校心理中心或专业机构。
- 回答使用简体中文，除非用户明确要求其他语言。
"""


def build_messages(history: list[dict[str, str]]) -> list[BaseMessage]:
    out: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    for m in history:
        role = m.get("role", "")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
    return out


def create_llm(*, streaming: bool) -> ChatOpenAI:
    kwargs: dict = {
        "model": get_model_name(),
        "api_key": get_openai_api_key(),
        "streaming": streaming,
        "temperature": 0.7,
    }
    base = get_base_url()
    if base:
        kwargs["base_url"] = base
    return ChatOpenAI(**kwargs)


async def stream_reply(history: list[dict[str, str]]) -> AsyncIterator[str]:
    llm = create_llm(streaming=True)
    messages = build_messages(history)
    async for chunk in llm.astream(messages):
        text = chunk.content
        if isinstance(text, str) and text:
            yield text
