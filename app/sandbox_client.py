import httpx
import json
from typing import Dict, Any

# 沙箱服务地址
SANDBOX_URL = "http://localhost:8000/execute"

async def execute_python_code(code: str, timeout: int = 60) -> Dict[str, Any]:
    """
    在 Docker 沙箱中执行 Python 代码，自动连接 Milvus
    
    参数:
        code: 要执行的 Python 代码字符串
        timeout: 超时时间（秒）
    
    返回:
        {
            "success": bool,
            "output": str,   # 代码执行的 stdout
            "error": str     # 如果有错误
        }
    """
    # 设置更长的超时时间，并正确处理参数
    timeout_config = httpx.Timeout(timeout=timeout + 10, connect=10.0)
    
    async with httpx.AsyncClient(timeout=timeout_config) as client:
        try:
            response = await client.post(
                SANDBOX_URL,
                json={"code": code, "timeout": timeout},
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except httpx.TimeoutException:
            return {
                "success": False,
                "output": "",
                "error": f"沙箱执行超时（{timeout}秒）"
            }
        except httpx.ConnectError as e:
            return {
                "success": False,
                "output": "",
                "error": f"无法连接到沙箱服务（{SANDBOX_URL}）：{str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }
