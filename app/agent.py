# agent.py
import json
import re
from collections.abc import AsyncIterator
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.config import get_base_url, get_model_name, get_openai_api_key, get_system_prompt

# 引入RAG工具，自动调用Milvus进行知识库管理和查询
from app.rag_client import search_knowledge

# 工具调用
from app.tools.jobMarketInfoTool import get_job_market_info
from app.tools.skillRequirementTool import get_skill_requirements
from app.tools.companyRecruitmentTool import get_company_recruitment
from app.tools.certificateInfoTool import get_certificate_info
from app.tools.milvusCodeTool import run_milvus_code

# ========== 辅助函数 ==========

def build_messages(history: list[dict[str, str]]) -> list[BaseMessage]:
    """构建消息历史"""
    out: list[BaseMessage] = [SystemMessage(content=get_system_prompt())]
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


def create_llm(*, streaming: bool = True, temperature: float = 0.7) -> ChatOpenAI:
    kwargs: Dict[str, Any] = {
        "model": get_model_name(),
        "api_key": get_openai_api_key(),
        "streaming": streaming,
        "temperature": temperature,
    }
    base = get_base_url()
    if(base):
        kwargs["base_url"] = base
    return ChatOpenAI(**kwargs)


def create_agent(streaming: bool = True) -> AgentExecutor:
    # 创建 Agent Executor
    llm = create_llm(streaming=streaming)

    tools = [
        get_job_market_info,
        get_skill_requirements,
        get_company_recruitment,
        get_certificate_info,
        run_milvus_code,
    ]

    prompt = ChatPromptTemplate.from_messages([
        ('system', get_system_prompt()),
        MessagesPlaceholder(variable_name='chat_history'),
        ('user', '{input}'),
        MessagesPlaceholder(variable_name='agent_scratchpad')
    ])

    agent = create_openai_tools_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=5,
    )

    return agent_executor


# ========== RAG 检索增强函数 ==========

async def enhance_query_with_rag(user_query: str, top_k: int = 3) -> tuple[str, List[Dict[str, Any]]]:
    """
    使用 RAG 检索增强用户查询
    
    返回:
        - enhanced_query: 增强后的查询文本（包含检索到的上下文）
        - retrieved_docs: 检索到的文档列表
    """
    try:
        # 从知识库检索相关内容
        search_result = await search_knowledge(user_query, top_k=top_k)
        
        # 解析搜索结果
        retrieved_docs = []
        context_parts = []
        
        # 如果搜索结果不为空且不是错误信息
        if search_result and "未找到" not in search_result and "失败" not in search_result:
            # 解析搜索结果中的内容
            # search_knowledge 返回格式化的文本，需要提取关键信息
            lines = search_result.split('\n')
            current_doc = {}
            
            for line in lines:
                if '【' in line and '】' in line and '相似度' in line:
                    if current_doc:
                        retrieved_docs.append(current_doc)
                        current_doc = {}
                elif '问题:' in line:
                    current_doc['question'] = line.split('问题:')[1].strip()
                elif '答案:' in line:
                    current_doc['answer'] = line.split('答案:')[1].strip()
                elif '分类:' in line:
                    current_doc['category'] = line.split('分类:')[1].strip()
            
            if current_doc:
                retrieved_docs.append(current_doc)
            
            # 构建上下文
            for i, doc in enumerate(retrieved_docs, 1):
                context_parts.append(f"""
【参考知识 {i}】
问题：{doc.get('question', '')}
答案：{doc.get('answer', '')}
分类：{doc.get('category', '')}
""")
            
            if context_parts:
                # 构建增强后的查询
                enhanced_query = f"""
用户问题：{user_query}

以下是知识库中相关的参考信息，请基于这些信息（结合你的专业知识）来回答用户问题：

{chr(10).join(context_parts)}

请综合以上参考信息，给出准确、详细的回答。如果参考信息不足以回答用户问题，请结合你的专业知识进行补充。
"""
                return enhanced_query, retrieved_docs
        
        return user_query, []
        
    except Exception as e:
        print(f"RAG 检索失败: {e}")
        return user_query, []


def extract_key_points_from_text(text: str) -> List[str]:
    """从自然语言文本中提取关键点"""
    if not text:
        return []

    # 优先从结构化段落提取：关键点/提示
    m = re.search(
        r'(?:【(?:关键点|提示)】|(?:关键点|提示)[：:])([\s\S]*?)(?:【建议】|建议[：:]|$)',
        text
    )
    if m:
        section = m.group(1)
        lines = [re.sub(r'^[\s\-*•·\d.、()（）]+', '', x).strip() for x in section.split('\n')]
        items = [x for x in lines if 5 < len(x) < 100]
        if items:
            return items[:3]
    
    key_points = []
    
    # 方法1：查找以数字或特殊符号开头的列表项
    bullet_patterns = [
        r'[•·\-*]\s*([^。\n]+)',  # • 项目符号
        r'(\d+)[.、）\)]\s*([^。\n]+)',  # 1. 2) 等
        r'[（(]\d+[）)]\s*([^。\n]+)',  # (1) 等
    ]
    
    for pattern in bullet_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # 如果是元组，取最后一个（非数字部分）
            point = match if isinstance(match, str) else match[-1]
            point = point.strip()
            if point and len(point) > 5 and len(point) < 100:
                key_points.append(point)
            if len(key_points) >= 3:
                return key_points[:3]
    
    # 方法2：查找包含关键词的句子
    keywords = ['重点', '关键', '主要', '包括', '例如', '比如', '特别是', '尤其是']
    sentences = re.split(r'[。！？；]', text)
    
    for sent in sentences:
        sent = sent.strip()
        if len(sent) > 10 and len(sent) < 100:
            if any(kw in sent for kw in keywords):
                key_points.append(sent)
            if len(key_points) >= 3:
                return key_points[:3]
    
    # 方法3：取前几个有意义的句子
    if not key_points and sentences:
        for sent in sentences[:3]:
            sent = sent.strip()
            if len(sent) > 10 and len(sent) < 100:
                key_points.append(sent)
    
    return key_points[:3]


def extract_suggestions_from_text(text: str) -> List[str]:
    """从自然语言文本中提取建议"""
    if not text:
        return []

    # 优先从结构化段落提取：建议
    m = re.search(r'(?:【建议】|建议[：:])([\s\S]*?)$', text)
    if m:
        section = m.group(1)
        lines = [re.sub(r'^[\s\-*•·\d.、()（）]+', '', x).strip() for x in section.split('\n')]
        items = [x for x in lines if 5 < len(x) < 150]
        if items:
            return items[:2]
    
    suggestions = []
    
    # 查找"建议"相关的段落
    if '建议' in text:
        # 分割文本
        parts = re.split(r'[。！？；]', text)
        
        for part in parts:
            if '建议' in part:
                # 提取建议内容
                suggestion = part.strip()
                # 清理前缀
                suggestion = re.sub(r'^.*?建议[：:]?\s*', '', suggestion)
                if suggestion and len(suggestion) > 5 and len(suggestion) < 150:
                    suggestions.append(suggestion)
            
            if len(suggestions) >= 2:
                break
    
    # 如果没有找到，查找包含"可以"、"需要"、"应该"的句子
    if not suggestions:
        keywords = ['可以', '需要', '应该', '推荐', '最好']
        sentences = re.split(r'[。！？；]', text)
        
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 5 and len(sent) < 100:
                if any(kw in sent for kw in keywords):
                    suggestions.append(sent)
                if len(suggestions) >= 2:
                    break
    
    return suggestions[:2]


async def stream_reply(history: list[dict[str, str]]) -> AsyncIterator[Dict[str, Any]]:
    """
    流式生成回复 - 自动使用 RAG 检索增强用户问题
    流程：用户提问 → RAG检索 → 增强查询 → Agent回答
    """
    
    # 获取最新的用户输入
    user_input = ""
    for m in reversed(history):
        if m.get("role") == "user":
            user_input = m.get("content", "")
            break
    
    # ========== 步骤1: RAG 检索增强 ==========
    # 发送 RAG 检索开始状态
    yield {
        "type": "rag_status",
        "content": "🔍 正在检索知识库...",
        "is_final": False
    }
    
    # 执行 RAG 检索
    enhanced_query, retrieved_docs = await enhance_query_with_rag(user_input, top_k=3)
    
    # 如果有检索到相关内容，发送检索结果摘要
    if retrieved_docs:
        print(retrieved_docs,"检索文献")
        yield {
            "type": "rag_result",
            "content": f"📚 找到 {len(retrieved_docs)} 条相关知识，正在生成回答...",
            "retrieved_count": len(retrieved_docs),
            "is_final": False
        }
    else:
        yield {
            "type": "rag_result",
            "content": "💡 未找到直接相关知识，将使用通用知识回答...",
            "is_final": False
        }
    
    # ========== 步骤2: 使用增强后的查询调用 Agent ==========
    agent_executor = create_agent(streaming=True)
    
    # 构建消息历史（保留之前的对话，但用增强后的查询替换当前用户输入）
    chat_history = build_messages(history[:-1]) if len(history) > 1 else []
    
    # 收集完整的响应
    full_response = []
    # 仅向前端流式输出正文，屏蔽末尾结构化段落（关键点/建议）
    struct_markers = ["【关键点】", "关键点：", "【提示】", "提示："]
    hold_len = max(len(m) for m in struct_markers) - 1
    stream_buffer = ""
    structured_started = False
    
    try:
        async for event in agent_executor.astream_events(
            {
                "input": (
                    enhanced_query
                    + "\n\n请在回答末尾严格追加以下结构化段落：\n"
                    + "【关键点】\n- 关键点1\n- 关键点2\n- 关键点3\n"
                    + "【建议】\n- 建议1\n- 建议2\n"
                    + "要求：每条一句话，简洁可执行。"
                ),  # 使用增强后的查询并要求结构化输出
                "chat_history": chat_history,
            },
            version="v1"
        ):
            # 捕获 LLM 流式输出
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    full_response.append(chunk.content)
                    stream_buffer += chunk.content

                    # 首次检测到结构化段落后，不再向前端透传其后内容
                    if not structured_started:
                        marker_pos = -1
                        for marker in struct_markers:
                            pos = stream_buffer.find(marker)
                            if pos != -1 and (marker_pos == -1 or pos < marker_pos):
                                marker_pos = pos

                        if marker_pos != -1:
                            structured_started = True
                            visible = stream_buffer[:marker_pos]
                            if visible:
                                yield {
                                    "type": "streaming",
                                    "content": visible,
                                    "is_final": False
                                }
                            stream_buffer = ""
                        elif len(stream_buffer) > hold_len:
                            visible = stream_buffer[:-hold_len]
                            if visible:
                                yield {
                                    "type": "streaming",
                                    "content": visible,
                                    "is_final": False
                                }
                            stream_buffer = stream_buffer[-hold_len:]

        # 若未进入结构化段落，补发缓冲区余量
        if stream_buffer and not structured_started:
            yield {
                "type": "streaming",
                "content": stream_buffer,
                "is_final": False
            }

        # 整合完整响应
        final_content = "".join(full_response)
        
        # 如果内容为空，返回默认回复
        if not final_content or len(final_content.strip()) < 10:
            final_content = "抱歉，我没有理解你的问题，请再详细说明一下你的专业和具体需求。"
        
        # 自动提取关键点和建议
        key_points = extract_key_points_from_text(final_content)
        suggestions = extract_suggestions_from_text(final_content)

        # 最终正文也去掉结构化段落，避免前端正文与卡片重复
        for marker in struct_markers:
            pos = final_content.find(marker)
            if pos != -1:
                final_content = final_content[:pos].rstrip()
                break
        
        # 最终结构化输出
        structured_output = {
            "type": "reply",
            "content": final_content,
            "key_points": key_points,
            "suggestions": suggestions,
            "retrieved_docs": retrieved_docs,  # 添加检索到的文档信息
            "data": {},
            "is_final": True,
        }
        
        yield structured_output
        
    except Exception as e:
        error_msg = f"抱歉，处理你的请求时出现了问题：{str(e)}"
        yield {
            "type": "error",
            "content": error_msg,
            "is_final": True,
            "error": str(e)
        }