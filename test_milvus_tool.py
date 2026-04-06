import asyncio
from app.sandbox_client import execute_python_code

async def test_milvus_operations():
    print("=" * 50)
    print("1. 测试查询 Milvus 版本")
    print("=" * 50)
    
    # 测试1：查询 Milvus 版本
    code1 = """from pymilvus import utility
print(f"Milvus 版本: {utility.get_server_version()}")
print(f"现有 Collections: {utility.list_collections()}")
"""
    result1 = await execute_python_code(code1)
    if result1.get("success"):
        print("✅ 成功")
        print(result1.get("output"))
    else:
        print(f"❌ 失败: {result1.get('error')}")
    
    print("\n" + "=" * 50)
    print("2. 测试创建 Collection")
    print("=" * 50)
    
    # 测试2：创建测试 Collection
    code2 = """from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

collection_name = "test_career_knowledge"

# 如果存在则删除
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)
    print(f"已删除旧 Collection: {collection_name}")

# 定义字段
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128),
    FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="answer", dtype=DataType.VARCHAR, max_length=2000),
    FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100)
]

schema = CollectionSchema(fields)
collection = Collection(collection_name, schema)

# 创建索引
index_params = {
    "metric_type": "COSINE",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 128}
}
collection.create_index(field_name="embedding", index_params=index_params)

print(f"✅ 成功创建 Collection: {collection_name}")
print(f"✅ 索引创建完成")
"""
    result2 = await execute_python_code(code2)
    if result2.get("success"):
        print("✅ 成功")
        print(result2.get("output"))
    else:
        print(f"❌ 失败: {result2.get('error')}")
    
    print("\n" + "=" * 50)
    print("3. 测试插入数据")
    print("=" * 50)
    
    # 测试3：插入测试数据
    code3 = """from pymilvus import Collection
import random

collection_name = "test_career_knowledge"
collection = Collection(collection_name)
collection.load()

# 准备测试数据（模拟一些向量）
vectors = [[random.random() for _ in range(128)] for _ in range(5)]
questions = [
    "计算机专业就业前景如何？",
    "如何准备算法面试？",
    "字节跳动校招时间是什么时候？",
    "PMP证书有用吗？",
    "前端开发需要学习哪些技术？"
]
answers = [
    "计算机专业就业前景广阔，平均起薪15-25k",
    "刷LeetCode，重点掌握动态规划和数据结构",
    "8-10月秋招，3-4月春招补录",
    "PMP国际认可，适合有经验的项目经理",
    "HTML/CSS/JS、React/Vue、构建工具"
]
categories = ["就业", "面试", "招聘", "证书", "技能"]

# 插入数据
collection.insert([vectors, questions, answers, categories])
collection.flush()

print(f"✅ 成功插入 {collection.num_entities} 条数据")
"""
    result3 = await execute_python_code(code3)
    if result3.get("success"):
        print("✅ 成功")
        print(result3.get("output"))
    else:
        print(f"❌ 失败: {result3.get('error')}")
    
    print("\n" + "=" * 50)
    print("4. 测试向量搜索")
    print("=" * 50)
    
    # 测试4：向量搜索
    code4 = """from pymilvus import Collection
import random

collection_name = "test_career_knowledge"
collection = Collection(collection_name)
collection.load()

# 创建一个查询向量（随机生成，实际应用中应该用 embedding 模型）
query_vector = [random.random() for _ in range(128)]

# 搜索参数
search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

# 执行搜索
results = collection.search(
    data=[query_vector],
    anns_field="embedding",
    param=search_params,
    limit=3,
    output_fields=["question", "answer", "category"]
)

print("搜索结果：")
for i, hits in enumerate(results):
    for hit in hits:
        print(f"  距离: {hit.distance:.4f}")
        print(f"  问题: {hit.entity.get('question')}")
        print(f"  答案: {hit.entity.get('answer')[:100]}...")
        print(f"  分类: {hit.entity.get('category')}")
        print()
"""
    result4 = await execute_python_code(code4)
    if result4.get("success"):
        print("✅ 成功")
        print(result4.get("output"))
    else:
        print(f"❌ 失败: {result4.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_milvus_operations())
