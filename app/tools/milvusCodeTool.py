# tools/milvusCodeTool.py - 正确版本
from langchain_core.tools import tool
from app.sandbox_client import execute_python_code

@tool
async def run_milvus_code(code: str) -> str:
    """执行自定义 Milvus 操作代码"""
    result = await execute_python_code(code, timeout=60)
    return result.get("output", result.get("error", "执行完成"))