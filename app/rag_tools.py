"""
RAG 查询工具 - 使用 Milvus 向量数据库进行智能检索
"""
import json
import asyncio
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

# 导入沙箱客户端
from app.sandbox_client import execute_python_code

# Embedding 配置（使用 OpenAI）
try:
    from langchain_openai import OpenAIEmbeddings
    from app.config import get_openai_api_key, get_base_url, get_model_name
    
    # 初始化 embedding 模型
    embedding_kwargs = {
        "model": "text-embedding-ada-002",  # OpenAI 的 embedding 模型
        "api_key": get_openai_api_key(),
    }
    base_url = get_base_url()
    if base_url:
        embedding_kwargs["base_url"] = base_url
    
    embeddings = OpenAIEmbeddings(**embedding_kwargs)
    EMBEDDINGS_AVAILABLE = True
    print("✅ OpenAI Embeddings 已加载")
    
except Exception as e:
    print(f"⚠️ OpenAI Embeddings 加载失败: {e}")
    print("将使用模拟 embedding（仅用于测试）")
    EMBEDDINGS_AVAILABLE = False
    # 创建模拟的 embedding 函数
    class MockEmbeddings:
        async def aembed_query(self, text: str) -> List[float]:
            """生成模拟的向量（仅用于测试）"""
            import hashlib
            import random
            # 使用文本的 hash 作为随机种子，保证相同文本产生相同向量
            hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            random.seed(hash_val)
            return [random.random() for _ in range(128)]
        
        def embed_query(self, text: str) -> List[float]:
            """同步版本的模拟 embedding"""
            import asyncio
            return asyncio.run(self.aembed_query(text))
    
    embeddings = MockEmbeddings()


def get_collection_name() -> str:
    """获取知识库 Collection 名称"""
    return "career_knowledge_base"


@tool
async def init_knowledge_base() -> str:
    """
    初始化知识库：创建 Milvus Collection 和索引。
    如果已存在则跳过。
    
    返回：
        初始化结果
    """
    collection_name = get_collection_name()
    
    code = f'''
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

collection_name = "{collection_name}"

# 检查是否已存在
if utility.has_collection(collection_name):
    print(f"✓ Collection '{collection_name}' 已存在，跳过创建")
    print(f"✓ 当前数据量: {{Collection(collection_name).num_entities}}")
else:
    # 定义字段
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128),
        FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="answer", dtype=DataType.VARCHAR, max_length=3000),
        FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="keywords", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=200)
    ]
    
    schema = CollectionSchema(fields, description="职业规划知识库")
    collection = Collection(collection_name, schema)
    
    # 创建索引
    index_params = {{
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {{"nlist": 128}}
    }}
    collection.create_index(field_name="embedding", index_params=index_params)
    
    print(f"✓ 成功创建 Collection: {{collection_name}}")
    print(f"✓ 索引创建完成")
'''
    
    result = await execute_python_code(code)
    if result.get("success"):
        return result.get("output", "初始化成功")
    else:
        return f"初始化失败: {result.get('error')}"


@tool
async def insert_knowledge(
    question: str,
    answer: str,
    category: str,
    keywords: str = "",
    source: str = "user_input"
) -> str:
    """
    向知识库插入一条知识条目（自动生成向量）。
    
    参数:
        question: 问题，如"计算机专业就业前景"
        answer: 答案，详细的回答内容
        category: 分类，如"就业"、"面试"、"证书"、"技能"
        keywords: 关键词，逗号分隔，如"计算机,就业,薪资"
        source: 来源，如"user_input"、"web_crawl"、"expert"
    
    返回：
        插入结果
    """
    collection_name = get_collection_name()
    
    # 生成问题的向量
    if EMBEDDINGS_AVAILABLE:
        embedding = await embeddings.aembed_query(question)
    else:
        embedding = embeddings.embed_query(question)
    
    # 转换为字符串格式
    embedding_str = str(embedding)
    
    code = f'''
from pymilvus import Collection

collection_name = "{collection_name}"
collection = Collection(collection_name)
collection.load()

# 准备数据
embedding = {embedding_str}
question = """{question}"""
answer = """{answer}"""
category = "{category}"
keywords = "{keywords}"
source = "{source}"

# 插入
mr = collection.insert([
    [embedding],           # embedding 列
    [question],            # question 列
    [answer],              # answer 列
    [category],            # category 列
    [keywords],            # keywords 列
    [source]               # source 列
])
collection.flush()

print(f"✓ 成功插入知识条目")
print(f"  - 问题: {{question[:50]}}...")
print(f"  - 分类: {{category}}")
print(f"  - 当前总数: {{collection.num_entities}}")
'''
    
    result = await execute_python_code(code)
    if result.get("success"):
        return result.get("output", "插入成功")
    else:
        return f"插入失败: {result.get('error')}"


@tool
async def search_knowledge(query: str, top_k: int = 3) -> str:
    """
    在知识库中搜索与问题最相关的内容。使用向量相似度检索。
    
    参数:
        query: 用户的问题，如"如何准备算法面试"
        top_k: 返回最相关的结果数量，默认为3
    
    返回：
        格式化的搜索结果，包含问题和答案
    """
    collection_name = get_collection_name()
    
    # 生成查询的向量
    if EMBEDDINGS_AVAILABLE:
        query_embedding = await embeddings.aembed_query(query)
    else:
        query_embedding = embeddings.embed_query(query)
    
    embedding_str = str(query_embedding)
    
    code = f'''
from pymilvus import Collection
import json

collection_name = "{collection_name}"
collection = Collection(collection_name)
collection.load()

# 查询向量
query_vector = {embedding_str}

# 搜索参数
search_params = {{
    "metric_type": "COSINE",
    "params": {{"nprobe": 10}}
}}

# 执行搜索
results = collection.search(
    data=[query_vector],
    anns_field="embedding",
    param=search_params,
    limit={top_k},
    output_fields=["question", "answer", "category", "keywords", "source"]
)

# 格式化输出
if not results or len(results[0]) == 0:
    print("未找到相关内容，请尝试其他关键词")
else:
    print(f"找到 {{len(results[0])}} 条相关内容：\\n")
    for i, hit in enumerate(results[0], 1):
        print(f"【结果 {{i}}】（相似度: {{hit.distance:.4f}}）")
        print(f"  问题: {{hit.entity.get('question')}}")
        print(f"  分类: {{hit.entity.get('category')}}")
        print(f"  答案: {{hit.entity.get('answer')[:200]}}...")
        if hit.entity.get('keywords'):
            print(f"  关键词: {{hit.entity.get('keywords')}}")
        print()
'''
    
    result = await execute_python_code(code)
    if result.get("success"):
        output = result.get("output", "")
        if not output.strip():
            return "未找到相关内容，请尝试其他关键词"
        return output
    else:
        return f"搜索失败: {result.get('error')}"


@tool
async def get_knowledge_stats() -> str:
    """
    获取知识库的统计信息：总条目数、分类分布等。
    
    返回：
        统计信息
    """
    collection_name = get_collection_name()
    
    code = f'''
from pymilvus import Collection, utility

collection_name = "{collection_name}"

if not utility.has_collection(collection_name):
    print("知识库尚未初始化，请先调用 init_knowledge_base")
else:
    collection = Collection(collection_name)
    collection.load()
    
    print(f"📊 知识库统计")
    print(f"  - Collection 名称: {{collection_name}}")
    print(f"  - 总条目数: {{collection.num_entities}}")
    
    # 获取分类分布（需要遍历，这里简化处理）
    print(f"  - 向量维度: 128")
    print(f"  - 索引类型: IVF_FLAT")
    print(f"  - 相似度度量: COSINE")
'''
    
    result = await execute_python_code(code)
    if result.get("success"):
        return result.get("output", "获取统计信息成功")
    else:
        return f"获取失败: {result.get('error')}"


@tool
async def batch_insert_knowledge(knowledge_list: str) -> str:
    """
    批量插入知识条目。
    
    参数:
        knowledge_list: JSON 格式的知识条目列表，格式：
            [
                {
                    "question": "问题",
                    "answer": "答案",
                    "category": "分类",
                    "keywords": "关键词",
                    "source": "来源"
                }
            ]
    
    返回：
        批量插入结果
    """
    try:
        items = json.loads(knowledge_list)
        if not isinstance(items, list):
            return "错误: knowledge_list 必须是 JSON 数组"
    except json.JSONDecodeError as e:
        return f"错误: JSON 解析失败 - {e}"
    
    collection_name = get_collection_name()
    
    # 生成所有问题的向量
    questions = [item["question"] for item in items]
    embeddings_list = []
    
    for q in questions:
        if EMBEDDINGS_AVAILABLE:
            emb = await embeddings.aembed_query(q)
        else:
            emb = embeddings.embed_query(q)
        embeddings_list.append(emb)
    
    # 构建批量插入代码
    embeddings_str = str(embeddings_list)
    questions_str = str(questions)
    answers_str = str([item["answer"] for item in items])
    categories_str = str([item.get("category", "未分类") for item in items])
    keywords_str = str([item.get("keywords", "") for item in items])
    sources_str = str([item.get("source", "batch_import") for item in items])
    
    code = f'''
from pymilvus import Collection

collection_name = "{collection_name}"
collection = Collection(collection_name)
collection.load()

# 准备批量数据
embeddings = {embeddings_str}
questions = {questions_str}
answers = {answers_str}
categories = {categories_str}
keywords = {keywords_str}
sources = {sources_str}

# 批量插入
mr = collection.insert([
    embeddings,
    questions,
    answers,
    categories,
    keywords,
    sources
])
collection.flush()

print(f"✓ 批量插入完成")
print(f"  - 成功插入: {{mr.insert_count}} 条")
print(f"  - 当前总数: {{collection.num_entities}} 条")
'''
    
    result = await execute_python_code(code)
    if result.get("success"):
        return result.get("output", f"成功插入 {len(items)} 条数据")
    else:
        return f"批量插入失败: {result.get('error')}"
