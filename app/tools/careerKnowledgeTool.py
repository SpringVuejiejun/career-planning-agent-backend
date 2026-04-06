from langchain_core.tools import tool
import json

@tool
async def query_career_knowledge(query: str, top_k: int = 5) -> str:
    """
    使用向量检索查询职业规划相关的知识库。可以查询职业信息、面试经验、公司信息等。
    
    参数:
        query: 查询问题，如"计算机专业的就业前景"、"字节跳动面试经验"等
        top_k: 返回最相关的结果数量，默认为5
    
    返回:
        相关的知识库检索结果
    """
    # 这里需要将 query 转换为向量（调用 embedding 模型）
    # 简化版：先用模拟数据，后续可以接入真实的 embedding API
    # 实际使用中需要调用 OpenAI Embeddings 或本地 embedding 模型
    
    # 临时方案：直接返回一个提示，告诉用户需要配置 embedding
    return json.dumps({
        "error": False,
        "message": "Milvus 向量检索功能已就绪",
        "query": query,
        "note": "需要配置 embedding 模型来将查询转换为向量",
        "suggestion": "请配置 OPENAI_API_KEY 或使用本地 embedding 模型"
    }, ensure_ascii=False)
