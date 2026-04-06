"""
RAG 客户端 - 使用阿里云 DashScope Embedding
"""
import asyncio
from app.sandbox_client import execute_python_code
from langchain_core.tools import tool

# 使用阿里云 DashScope Embeddings
try:
    from langchain_community.embeddings import DashScopeEmbeddings
    from app.config import get_dashscope_api_key
    
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v1",  # 阿里云文本向量模型
        dashscope_api_key=get_dashscope_api_key(),
    )
    EMBEDDINGS_AVAILABLE = True
except Exception as e:
    print(f"⚠️ DashScope Embeddings 加载失败: {e}")
    print("将使用模拟向量")
    EMBEDDINGS_AVAILABLE = False


def get_collection_name() -> str:
    return "career_knowledge_base"

# @tool(description="初始化知识库：创建 Milvus Collection 和索引")
async def init_knowledge_base() -> str:
    """初始化知识库"""
    collection_name = get_collection_name()
    
    code = f'''
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

collection_name = "{collection_name}"

if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)
    print(f"✓ 已删除旧 Collection")

# 创建新 Collection（DashScope text-embedding-v1 维度是 1536）
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
    FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="answer", dtype=DataType.VARCHAR, max_length=3000),
    FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
    FieldSchema(name="keywords", dtype=DataType.VARCHAR, max_length=500)
]
schema = CollectionSchema(fields, description="职业规划知识库")
collection = Collection(collection_name, schema)

# 创建索引
index_params = {{"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {{"nlist": 128}}}}
collection.create_index(field_name="embedding", index_params=index_params)
print(f"✓ Collection '{{collection_name}}' 创建成功 (维度: 1536)")
'''
    result = await execute_python_code(code)
    output = result.get("output", result.get("error", "初始化完成"))
    # 过滤掉连接信息
    import re
    output = re.sub(r'✓ 成功连接到Milvus: .*\n', '', output)
    return output

# @tool(description="插入知识条目到 Milvus 知识库")
async def insert_knowledge(question: str, answer: str, category: str, keywords: str = "") -> str:
    """插入知识条目"""
    collection_name = get_collection_name()
    
    # 生成向量
    if EMBEDDINGS_AVAILABLE:
        embedding = await embeddings.aembed_query(question)
    else:
        # 模拟向量
        import random
        random.seed(hash(question) % 2**32)
        embedding = [random.random() for _ in range(1536)]
    
    embedding_str = str(embedding)
    
    code = f'''
from pymilvus import Collection

collection = Collection("{collection_name}")
collection.load()

embedding = {embedding_str}
question = \"\"\"{question}\"\"\"
answer = \"\"\"{answer}\"\"\"
category = "{category}"
keywords = "{keywords}"

collection.insert([
    [embedding], [question], [answer], [category], [keywords]
])
collection.flush()

print(f"✓ 插入成功: {{question[:50]}}...")
print(f"  分类: {{category}}")
print(f"  当前总数: {{collection.num_entities}}")
'''
    result = await execute_python_code(code)
    output = result.get("output", result.get("error", "插入完成"))
    import re
    output = re.sub(r'✓ 成功连接到Milvus: .*\n', '', output)
    return output

# @tool(description="搜索知识库")
async def search_knowledge(query: str, top_k: int = 3) -> str:
    """搜索知识库"""
    collection_name = get_collection_name()
    
    # 生成查询向量
    if EMBEDDINGS_AVAILABLE:
        query_embedding = await embeddings.aembed_query(query)
    else:
        import random
        random.seed(hash(query) % 2**32)
        query_embedding = [random.random() for _ in range(1536)]
    
    embedding_str = str(query_embedding)
    
    code = f'''
from pymilvus import Collection

collection = Collection("{collection_name}")
collection.load()

query_vector = {embedding_str}

search_params = {{"metric_type": "COSINE", "params": {{"nprobe": 10}}}}

results = collection.search(
    data=[query_vector],
    anns_field="embedding",
    param=search_params,
    limit={top_k},
    output_fields=["question", "answer", "category", "keywords"]
)

if not results or len(results[0]) == 0:
    print("未找到相关内容")
else:
    print(f"找到 {{len(results[0])}} 条相关结果：\\n")
    for i, hit in enumerate(results[0], 1):
        print(f"【{{i}}】相似度: {{hit.distance:.4f}}")
        print(f"  问题: {{hit.entity.get('question')}}")
        print(f"  分类: {{hit.entity.get('category')}}")
        print(f"  答案: {{hit.entity.get('answer')[:150]}}...")
        print()
'''
    result = await execute_python_code(code)
    output = result.get("output", "")
    if not output.strip():
        return "未找到相关内容"
    import re
    output = re.sub(r'✓ 成功连接到Milvus: .*\n', '', output)
    return output

# @tool(description="获取知识库统计信息")
async def get_stats() -> str:
    """获取统计信息"""
    collection_name = get_collection_name()
    
    code = f'''
from pymilvus import Collection, utility

if not utility.has_collection("{collection_name}"):
    print("知识库未初始化")
else:
    collection = Collection("{collection_name}")
    collection.load()
    print(f"知识库统计:")
    print(f"  - 总条目数: {{collection.num_entities}}")
    print(f"  - 向量维度: 1536")
'''
    result = await execute_python_code(code)
    output = result.get("output", "获取统计信息失败")
    import re
    output = re.sub(r'✓ 成功连接到Milvus: .*\n', '', output)
    return output
