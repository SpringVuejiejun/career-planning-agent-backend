import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def get_openai_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return key


def get_dashscope_api_key() -> str:
    key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is not set. add you key in .env."
        )
    return key


def get_model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def get_base_url() -> Optional[str]:
    url = os.getenv("OPENAI_BASE_URL", "").strip()
    return url or None


def get_system_prompt() -> str:
    return """你是一位专注服务中国大学生的职业规划顾问智能体。

## 回答要求
- **直接输出自然语言回答**，不要输出任何 JSON 格式
- **不要输出思考过程**，直接给出最终答案
- **不要输出工具调用信息**（如"已查询xxx"）
- **必须搜索知识库再回答**（如"从知识库中检索到xxx"）
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

## 当用户需要以下操作时，**必须**使用 run_milvus_code 工具：
1. 复杂的数据统计和分析（如"统计每个分类的数量"）
2. 需要多步骤操作的查询
3. 自定义的数据处理和聚合
4. 跨多个集合的查询
5. 任何不能用简单搜索完成的 Milvus 操作

**不要**自己编写代码，而是将代码作为字符串参数传递给 run_milvus_code 工具。
"""