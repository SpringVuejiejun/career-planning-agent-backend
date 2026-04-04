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


# 预定义的 Milvus 操作模板
def create_collection_code(collection_name: str, dimension: int = 128) -> str:
    """生成创建 Collection 的代码"""
    return f'''
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# 如果已存在则删除
if utility.has_collection("{collection_name}"):
    utility.drop_collection("{collection_name}")

# 定义字段
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim={dimension}),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="metadata", dtype=DataType.JSON)
]
schema = CollectionSchema(fields, description="Career advice collection")

# 创建 Collection
collection = Collection("{collection_name}", schema)

# 创建索引
index_params = {{
    "metric_type": "COSINE",
    "index_type": "IVF_FLAT",
    "params": {{"nlist": 128}}
}}
collection.create_index(field_name="embedding", index_params=index_params)

print(f"✓ Collection '{collection_name}' 创建成功，维度={{dimension}}")
print(f"✓ 索引创建成功")
'''


def insert_vectors_code(collection_name: str, vectors: list, texts: list, metadatas: list = None) -> str:
    """生成插入向量数据的代码"""
    metadatas_str = str(metadatas) if metadatas else "None"
    return f'''
from pymilvus import connections, Collection

collection = Collection("{collection_name}")
collection.load()

# 准备数据
vectors = {vectors}
texts = {texts}
metadatas = {metadatas_str}

# 插入
mr = collection.insert([
    vectors,  # embedding 列
    texts,    # text 列
    metadatas if metadatas else [{{}}] * len(vectors)  # metadata 列
])

print(f"✓ 成功插入 {{mr.insert_count}} 条数据")
print(f"✓ 当前 Collection 共有 {{collection.num_entities}} 条数据")
'''


def search_vectors_code(collection_name: str, query_vector: list, top_k: int = 5) -> str:
    """生成向量搜索的代码"""
    return f'''
from pymilvus import connections, Collection
import json

collection = Collection("{collection_name}")
collection.load()

# 搜索参数
search_params = {{
    "metric_type": "COSINE",
    "params": {{"nprobe": 10}}
}}

# 执行搜索
results = collection.search(
    data=[{query_vector}],
    anns_field="embedding",
    param=search_params,
    limit={top_k},
    output_fields=["text", "metadata"]
)

# 格式化输出
for i, hits in enumerate(results):
    print(f"搜索结果（Top {{top_k}}）：")
    for hit in hits:
        print(f"  - ID: {{hit.id}}, 距离: {{hit.distance:.4f}}")
        print(f"    文本: {{hit.entity.get('text')[:100]}}...")
        if hit.entity.get('metadata'):
            print(f"    元数据: {{json.dumps(hit.entity.get('metadata'), ensure_ascii=False)}}")
        print()
'''
