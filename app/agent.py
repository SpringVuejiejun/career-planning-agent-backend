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

from app.config import get_base_url, get_model_name, get_openai_api_key


# ========== 系统提示词（要求结构化输出） ==========
SYSTEM_PROMPT = """你是一位专注服务中国大学生的职业规划顾问智能体。

## 回答要求
- **直接输出自然语言回答**，不要输出任何 JSON 格式
- **不要输出思考过程**，直接给出最终答案
- **不要输出工具调用信息**（如"已查询xxx"）
- 语气友好、专业、具体
- 回答使用简体中文

## 回答示例

用户问："计算机专业就业怎么样？"
你回答：
计算机专业的就业前景非常好，尤其是在北京、上海、深圳等一线城市。平均起薪在15-25k之间，就业率超过90%。建议提前刷LeetCode，多积累项目经验，关注秋招时间8-10月。

用户问："字节跳动的校招信息"
你回答：
字节跳动的校招主要集中在每年8月到10月，部分岗位在春招也会有补录。面试时非常看重算法能力，LeetCode中等难度的题比较常见，还会深入追问项目经历。岗位包括后端、前端、算法、客户端等，工作地点在北京、上海、深圳、杭州、广州都能选。

## 工作原则
- 需要更多信息时，直接追问用户
- 涉及数据时尽量具体
"""


# ========== 定义工具 ==========

@tool
async def get_job_market_info(major: str, city: str = "全国") -> str:
    """
    获取指定专业在特定城市的就业市场信息。
    
    参数:
        major: 专业名称，如"计算机科学与技术"、"金融学"等
        city: 城市名称，默认为"全国"
    
    返回:
        包含薪资、就业率、主要行业等的就业信息
    """
    # 模拟数据（实际使用时替换为真实API）
    market_data = {
        "计算机科学与技术": {
            "全国": {
                "salary": "15-25k",
                "rate": "92%",
                "industries": ["互联网", "金融科技", "国企IT"],
                "description": "就业前景广阔，薪资待遇好"
            },
            "北京": {
                "salary": "18-30k",
                "rate": "94%",
                "industries": ["互联网大厂", "金融IT", "人工智能"],
                "description": "大厂集中，机会多"
            },
            "上海": {
                "salary": "17-28k",
                "rate": "93%",
                "industries": ["金融科技", "互联网", "外企"],
                "description": "金融和互联网并重"
            },
            "深圳": {
                "salary": "18-28k",
                "rate": "95%",
                "industries": ["硬件科技", "互联网", "通信"],
                "description": "科技公司聚集地"
            }
        },
        "金融学": {
            "全国": {
                "salary": "10-20k",
                "rate": "85%",
                "industries": ["银行", "证券", "基金"],
                "description": "稳定但竞争激烈"
            },
            "上海": {
                "salary": "15-25k",
                "rate": "88%",
                "industries": ["投行", "基金", "信托"],
                "description": "金融中心，高端岗位多"
            },
            "北京": {
                "salary": "14-24k",
                "rate": "87%",
                "industries": ["银行总部", "券商", "监管机构"],
                "description": "总部经济，稳定性好"
            }
        }
    }
    
    if major not in market_data:
        return json.dumps({
            "error": True,
            "message": f"暂时没有{major}专业的详细就业数据",
            "suggestion": "建议查看教育部官方就业报告或学校就业指导中心"
        }, ensure_ascii=False)
    
    city_data = market_data[major].get(city, market_data[major]["全国"])
    
    return json.dumps({
        "error": False,
        "major": major,
        "city": city,
        "salary": city_data["salary"],
        "employment_rate": city_data["rate"],
        "industries": city_data["industries"],
        "description": city_data["description"]
    }, ensure_ascii=False)


@tool
async def get_skill_requirements(job_title: str) -> str:
    """
    获取特定职位所需的技能要求。
    
    参数:
        job_title: 职位名称，如"前端开发工程师"、"产品经理"等
    
    返回:
        该职位的技能要求、学习路径和建议
    """
    skills_data = {
        "后端开发工程师": {
            "core_skills": ["Java/Go/Python", "数据库", "Linux", "分布式系统"],
            "learning_path": ["语言基础(1-2月)", "框架学习(2-3月)", "项目实战(2-3月)"],
            "salary_range": "20-35k",
            "difficulty": "较高"
        },
        "前端开发工程师": {
            "core_skills": ["HTML/CSS/JS", "React/Vue", "构建工具", "浏览器原理"],
            "learning_path": ["基础三件套(2-3月)", "框架进阶(2-3月)", "工程化(1-2月)"],
            "salary_range": "18-30k",
            "difficulty": "中等"
        },
        "算法工程师": {
            "core_skills": ["Python", "机器学习", "深度学习", "数据结构"],
            "learning_path": ["数学基础(2-3月)", "ML/DL算法(3-4月)", "论文复现(2-3月)"],
            "salary_range": "25-45k",
            "difficulty": "高"
        },
        "产品经理": {
            "core_skills": ["用户研究", "原型设计", "数据分析", "沟通协调"],
            "learning_path": ["产品思维(1-2月)", "工具使用(1月)", "实战项目(2-3月)"],
            "salary_range": "15-30k",
            "difficulty": "中等"
        }
    }
    
    if job_title not in skills_data:
        return json.dumps({
            "error": True,
            "message": f"暂时没有{job_title}的详细技能要求",
            "suggestion": "建议查看招聘网站或行业报告"
        }, ensure_ascii=False)
    
    data = skills_data[job_title]
    return json.dumps({
        "error": False,
        "job_title": job_title,
        "core_skills": data["core_skills"],
        "learning_path": data["learning_path"],
        "salary_range": data["salary_range"],
        "difficulty": data["difficulty"]
    }, ensure_ascii=False)


@tool
async def get_company_recruitment(company_name: str, job_type: str = "校招") -> str:
    """
    查询特定公司的校招/实习信息。
    
    参数:
        company_name: 公司名称，如"字节跳动"、"腾讯"
        job_type: 职位类型，可选"实习"、"校招"，默认为"校招"
    
    返回:
        该公司的招聘信息和申请建议
    """
    companies_data = {
        "字节跳动": {
            "校招": {
                "time": "8-10月（秋招），3-4月（春招补录）",
                "key_points": ["非常注重算法能力", "项目深度追问", "技术栈灵活"],
                "interviews": ["LeetCode中等/困难", "系统设计", "项目深挖"],
                "positions": ["后端", "前端", "算法", "客户端", "测开", "产品"],
                "locations": ["北京", "上海", "深圳", "杭州", "广州"],
                "tips": ["刷LeetCode150题以上", "准备项目难点和优化思路", "关注官方招聘号"]
            },
            "实习": {
                "time": "全年可投，暑期实习机会最多",
                "key_points": ["转正机会大", "面试难度略低于校招", "看重基础"],
                "interviews": ["LeetCode简单/中等", "基础知识", "项目经验"],
                "positions": ["技术岗为主", "产品岗", "运营岗"],
                "locations": ["北京", "上海", "深圳"],
                "tips": ["提前3-6个月准备", "争取内推", "实习经历很重要"]
            }
        },
        "腾讯": {
            "校招": {
                "time": "8-10月（秋招），3-4月（春招）",
                "key_points": ["注重计算机基础", "C++/Go技术栈", "重视项目"],
                "interviews": ["操作系统", "网络", "算法", "项目"],
                "positions": ["后端", "客户端", "游戏开发", "产品"],
                "locations": ["深圳", "北京", "上海", "广州", "成都"],
                "tips": ["加强C++", "准备网络和操作系统", "有开源经历加分"]
            }
        },
        "阿里巴巴": {
            "校招": {
                "time": "7-9月（秋招），3-4月（春招）",
                "key_points": ["Java技术栈", "重视中间件", "看重项目"],
                "interviews": ["Java基础", "JVM", "并发", "框架源码"],
                "positions": ["后端", "前端", "算法", "测试"],
                "locations": ["杭州", "北京", "上海", "深圳"],
                "tips": ["精通Java", "研究Spring源码", "有高并发经验加分"]
            }
        }
    }
    
    if company_name not in companies_data:
        return json.dumps({
            "error": True,
            "message": f"暂时没有{company_name}的详细招聘信息",
            "suggestion": "建议关注公司官网招聘页面或牛客网"
        }, ensure_ascii=False)
    
    company = companies_data[company_name]
    info = company.get(job_type, company.get("校招", {}))
    
    return json.dumps({
        "error": False,
        "company": company_name,
        "job_type": job_type,
        "recruitment_time": info.get("time", "关注官方通知"),
        "key_points": info.get("key_points", []),
        "interview_focus": info.get("interviews", []),
        "positions": info.get("positions", []),
        "locations": info.get("locations", []),
        "tips": info.get("tips", [])
    }, ensure_ascii=False)


@tool
async def get_certificate_info(cert_name: str) -> str:
    """
    查询职业认证证书的相关信息。
    
    参数:
        cert_name: 证书名称，如"PMP"、"CPA"
    
    返回:
        证书的价值、考试要求
    """
    certs_data = {
        "PMP": {
            "full_name": "项目管理专业人士认证",
            "value": "国际认可，适合有经验的项目经理",
            "requirements": "35学时培训 + 考试经验",
            "cost": "约3900元",
            "difficulty": "中等",
            "time": "3-6个月准备"
        },
        "CPA": {
            "full_name": "注册会计师",
            "value": "国内含金量最高，财会领域必备",
            "requirements": "专科以上学历",
            "cost": "每科约70元",
            "difficulty": "高",
            "time": "2-3年"
        },
        "软考": {
            "full_name": "计算机技术与软件专业技术资格",
            "value": "国企事业单位认可，可评职称",
            "requirements": "无学历要求",
            "cost": "约200元",
            "difficulty": "中等",
            "time": "2-3个月"
        }
    }
    
    if cert_name not in certs_data:
        return json.dumps({
            "error": True,
            "message": f"暂时没有{cert_name}的详细信息",
            "suggestion": "建议查看官方考试网站"
        }, ensure_ascii=False)
    
    data = certs_data[cert_name]
    return json.dumps({
        "error": False,
        "cert_name": cert_name,
        "full_name": data["full_name"],
        "value": data["value"],
        "requirements": data["requirements"],
        "cost": data["cost"],
        "difficulty": data["difficulty"],
        "preparation_time": data["time"]
    }, ensure_ascii=False)


# ========== 辅助函数 ==========

def build_messages(history: list[dict[str, str]]) -> list[BaseMessage]:
    """构建消息历史"""
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


def create_llm(*, streaming: bool = True, temperature: float = 0.7) -> ChatOpenAI:
    """创建 LLM 实例"""
    kwargs: Dict[str, Any] = {
        "model": get_model_name(),
        "api_key": get_openai_api_key(),
        "streaming": streaming,
        "temperature": temperature,
    }
    base = get_base_url()
    if base:
        kwargs["base_url"] = base
    return ChatOpenAI(**kwargs)


def create_agent(streaming: bool = True) -> AgentExecutor:
    """创建 Agent Executor"""
    
    tools = [
        get_job_market_info,
        get_skill_requirements,
        get_company_recruitment,
        get_certificate_info,
    ]
    
    llm = create_llm(streaming=streaming)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_openai_tools_agent(llm, tools, prompt)
    
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,  # 生产环境设为False
        handle_parsing_errors=True,
        max_iterations=5,
    )
    
    return agent_executor


def extract_json_from_response(content: str) -> Dict[str, Any]:
    """从 Agent 回复中提取 JSON"""
    
    # 尝试直接解析
    try:
        return json.loads(content)
    except:
        pass
    
    # 尝试提取 JSON 块
    json_pattern = r'\{[^{}]*\}'
    matches = re.findall(json_pattern, content, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match)
        except:
            continue
    
    # 如果都失败，返回默认结构
    return {
        "type": "reply",
        "content": content,
        "key_points": [],
        "suggestions": [],
        "data": {},
        "needs_more_info": False,
        "follow_up_question": ""
    }


# ========== 主要流式接口 ==========
async def get_reply(history: list[dict[str, str]]) -> Dict[str, Any]:
    """非流式获取完整回复（返回最终的结构化 JSON）"""
    final_result = None
    async for chunk in stream_reply(history):
        if chunk.get("is_final"):
            final_result = chunk
    return final_result or {
        "type": "error",
        "content": "未能获取到有效回复",
        "is_final": True
    }

# agent.py - 修改 stream_reply 函数

import re
from collections.abc import AsyncIterator
from typing import Dict, Any, List
from datetime import datetime

# ... 其他导入保持不变 ...

def extract_key_points_from_text(text: str) -> List[str]:
    """从自然语言文本中提取关键点"""
    if not text:
        return []
    
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
    流式生成回复 - 显示简化的工具状态，自动提取关键点和建议
    """
    
    agent_executor = create_agent(streaming=True)
    
    # 构建输入
    chat_history = build_messages(history[:-1]) if len(history) > 1 else []
    
    # 获取最新的用户输入
    user_input = ""
    for m in reversed(history):
        if m.get("role") == "user":
            user_input = m.get("content", "")
            break
    
    # 收集完整的响应
    full_response = []
    has_shown_tool_status = False
    
    try:
        async for event in agent_executor.astream_events(
            {
                "input": user_input,
                "chat_history": chat_history,
            },
            version="v1"
        ):
            # 捕获 LLM 流式输出
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    full_response.append(chunk.content)
                    
                    # 实时流式输出（只输出内容，不解析）
                    yield {
                        "type": "streaming",
                        "content": chunk.content,
                        "is_final": False
                    }
            
            # 捕获工具调用开始 - 显示简化的状态
            elif event["event"] == "on_tool_start":
                tool_name = event.get("name", "")
                # 将工具名转换为用户友好的提示
                tool_display = {
                    "get_job_market_info": "正在查询就业市场信息",
                    "get_skill_requirements": "正在查询技能要求",
                    "get_company_recruitment": "正在查询公司招聘信息",
                    "get_certificate_info": "正在查询证书信息",
                }.get(tool_name, f"正在查询{tool_name}")
                
                # 发送工具状态（前端可以显示 loading 提示）
                yield {
                    "type": "tool_status",
                    "content": tool_display,
                    "tool": tool_name,
                    "status": "running",
                    "is_final": False
                }
                has_shown_tool_status = True
            
            # 捕获工具调用结束 - 可以发送完成状态（可选）
            elif event["event"] == "on_tool_end":
                tool_name = event.get("name", "")
                yield {
                    "type": "tool_status",
                    "content": "查询完成",
                    "tool": tool_name,
                    "status": "completed",
                    "is_final": False
                }
        
        # 整合完整响应
        final_content = "".join(full_response)
        
        # 清理内容（移除可能的 JSON 残留）
        final_content = clean_agent_response(final_content)
        
        # 如果内容为空，返回默认回复
        if not final_content or len(final_content.strip()) < 10:
            final_content = "抱歉，我没有理解你的问题，请再详细说明一下你的专业和具体需求。"
        
        # 自动提取关键点和建议
        key_points = extract_key_points_from_text(final_content)
        suggestions = extract_suggestions_from_text(final_content)
        
        # 最终结构化输出
        structured_output = {
            "type": "reply",
            "content": final_content,
            "key_points": key_points,
            "suggestions": suggestions,
            "data": {},
            "is_final": True,
            "timestamp": datetime.now().isoformat()
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


def clean_agent_response(response: str) -> str:
    """清理 Agent 响应中的 JSON 残留"""
    if not response:
        return ""
    
    cleaned = response
    
    # 移除可能的 JSON 格式残留
    cleaned = re.sub(r'\{[^{}]*\}', '', cleaned, flags=re.DOTALL)
    
    # 移除 "data: " 前缀
    cleaned = re.sub(r'^data:\s*', '', cleaned, flags=re.MULTILINE)
    
    # 移除多余的引号
    cleaned = re.sub(r'^"|"$', '', cleaned.strip())
    
    # 清理空白
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
    cleaned = cleaned.strip()
    
    # 如果清理后以逗号开头，移除逗号
    if cleaned.startswith(','):
        cleaned = cleaned[1:].strip()
    
    return cleaned