# # init_rag_data.py
# import asyncio
# from app.rag_client import init_knowledge_base, insert_knowledge, get_stats

# async def init_knowledge_base_data():
#     """初始化知识库并插入测试数据"""
    
#     # 1. 初始化知识库
#     print("正在初始化知识库...")
#     result = await init_knowledge_base()
#     print(result)
    
#     # 2. 插入职业规划相关数据
#     knowledge_data = [
#         {
#             "question": "如何准备技术面试？",
#             "answer": "技术面试准备要点：1. 刷LeetCode算法题（建议200+）2. 准备系统设计题目 3. 复习计算机基础知识（网络、操作系统、数据库）4. 准备项目经验介绍 5. 准备行为面试问题",
#             "category": "面试技巧",
#             "keywords": "面试,算法,系统设计"
#         },
#         {
#             "question": "如何从开发转向架构师？",
#             "answer": "从开发转向架构师的路径：1. 深入理解系统设计原则 2. 学习分布式系统架构 3. 掌握多种技术栈 4. 培养全局思维和业务理解能力 5. 参与高并发系统设计 6. 考取架构师认证",
#             "category": "职业发展",
#             "keywords": "架构师,职业规划,技术成长"
#         },
#         {
#             "question": "前端开发的学习路径是什么？",
#             "answer": "前端开发学习路径：1. HTML/CSS基础 2. JavaScript核心 3. React/Vue框架 4. 工程化工具（Webpack）5. Node.js 6. TypeScript 7. 性能优化 8. 移动端开发",
#             "category": "技术路线",
#             "keywords": "前端,学习路径,Web开发"
#         },
#         {
#             "question": "如何准备产品经理面试？",
#             "answer": "产品经理面试准备：1. 产品思维和案例分析 2. 数据分析和指标设计 3. 用户体验设计 4. 市场需求分析 5. 竞品分析 6. 项目经验复盘 7. 行为面试准备",
#             "category": "面试技巧",
#             "keywords": "产品经理,面试,产品思维"
#         },
#         {
#             "question": "数据科学家需要掌握哪些技能？",
#             "answer": "数据科学家核心技能：1. Python/R编程 2. SQL数据库 3. 统计学和数学 4. 机器学习算法 5. 数据可视化 6. 大数据技术（Spark）7. 业务理解和沟通能力",
#             "category": "技能要求",
#             "keywords": "数据科学,机器学习,技能"
#         },
#         {
#             "question": "如何提升编程能力？",
#             "answer": "提升编程能力的方法：1. 每天坚持编码 2. 参与开源项目 3. 阅读优秀源码 4. 解决实际问题 5. 学习设计模式 6. 代码审查和重构 7. 写技术博客",
#             "category": "技能提升",
#             "keywords": "编程,技能提升,学习方法"
#         }
#     ]
    
#     print("\n正在插入知识数据...")
#     for data in knowledge_data:
#         result = await insert_knowledge(
#             question=data["question"],
#             answer=data["answer"],
#             category=data["category"],
#             keywords=data["keywords"]
#         )
#         print(f"✓ 插入: {data['question'][:30]}...")
#         print(f"  结果: {result}\n")
    
#     # 3. 查看统计
#     stats = await get_stats()
#     print(f"\n📊 最终统计:\n{stats}")

# async def test_search():
#     """测试搜索功能"""
#     print("\n" + "="*50)
#     print("测试搜索功能")
#     print("="*50)
    
#     test_queries = [
#         "如何准备面试",
#         "怎么成为架构师",
#         "前端学习路线",
#         "数据科学家需要什么"
#     ]
    
#     from app.rag_client import search_knowledge
    
#     for query in test_queries:
#         print(f"\n🔍 搜索: {query}")
#         result = await search_knowledge(query, top_k=2)
#         print(f"结果:\n{result}\n")

# if __name__ == "__main__":
#     asyncio.run(init_knowledge_base_data())
#     asyncio.run(test_search())





# check_rag.py
import asyncio
from app.rag_client import get_stats, search_knowledge

async def check_rag_status():
    """检查RAG知识库状态"""
    print("检查RAG知识库状态")
    print("="*50)
    
    # 1. 获取统计信息
    stats = await get_stats()
    print(f"\n📊 知识库统计:\n{stats}")
    
    # 2. 测试检索
    test_query = "面试"
    print(f"\n🔍 测试检索: '{test_query}'")
    result = await search_knowledge(test_query, top_k=3)
    print(f"检索结果:\n{result}")
    
    # 3. 检查是否真的有数据
    if "总条目数: 0" in stats or "知识库未初始化" in stats:
        print("\n⚠️ 知识库为空！请先运行 init_rag_data.py 初始化数据")
    else:
        print("\n✅ 知识库已有数据")

if __name__ == "__main__":
    asyncio.run(check_rag_status())
