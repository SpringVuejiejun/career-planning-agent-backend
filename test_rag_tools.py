import asyncio
from app.rag_tools import init_knowledge_base, insert_knowledge, search_knowledge, get_knowledge_stats

async def test_rag():
    print("=" * 60)
    print("1. 初始化知识库")
    print("=" * 60)
    # 直接调用底层函数，而不是通过 LangChain 工具
    result = await init_knowledge_base.func("")  # 工具函数需要参数
    print(result)
    
    print("\n" + "=" * 60)
    print("2. 插入知识条目")
    print("=" * 60)
    result = await insert_knowledge.func(
        question="计算机专业就业前景如何？",
        answer="计算机专业就业前景非常好，平均起薪15-25k，就业率超过90%。主要就业方向包括：后端开发、前端开发、算法工程师、运维开发等。建议在校期间多积累项目经验，刷LeetCode准备面试。",
        category="就业",
        keywords="计算机,就业,薪资,方向",
        source="expert"
    )
    print(result)
    
    result = await insert_knowledge.func(
        question="如何准备字节跳动的面试？",
        answer="字节跳动面试非常注重算法能力，LeetCode中等难度题很常见。面试流程：简历筛选 -> 笔试 -> 2-3轮技术面 -> HR面。建议：刷LeetCode150题以上，深入准备项目经历，关注系统设计。",
        category="面试",
        keywords="字节跳动,面试,算法,LeetCode",
        source="expert"
    )
    print(result)
    
    result = await insert_knowledge.func(
        question="PMP证书值得考吗？",
        answer="PMP（项目管理专业人士）证书国际认可度高，适合有3年以上项目管理经验的人。考试费用约3900元，需要35学时培训。持证后平均薪资提升20%以上，尤其在外企和大型项目中很受认可。",
        category="证书",
        keywords="PMP,项目管理,证书,考试",
        source="expert"
    )
    print(result)
    
    print("\n" + "=" * 60)
    print("3. 获取知识库统计")
    print("=" * 60)
    result = await get_knowledge_stats.func("")
    print(result)
    
    print("\n" + "=" * 60)
    print("4. 搜索知识（测试向量检索）")
    print("=" * 60)
    result = await search_knowledge.func(query="算法面试怎么准备", top_k=2)
    print(result)
    
    print("\n" + "=" * 60)
    print("5. 搜索另一个问题")
    print("=" * 60)
    result = await search_knowledge.func(query="计算机专业工资多少", top_k=2)
    print(result)

if __name__ == "__main__":
    asyncio.run(test_rag())
