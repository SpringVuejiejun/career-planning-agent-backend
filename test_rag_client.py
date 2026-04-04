import asyncio
from app.rag_client import init_knowledge_base, insert_knowledge, search_knowledge, get_stats

async def test():
    print("=" * 60)
    print("1. 初始化知识库")
    print("=" * 60)
    result = await init_knowledge_base()
    print(result)
    
    print("\n" + "=" * 60)
    print("2. 插入知识条目")
    print("=" * 60)
    result = await insert_knowledge(
        question="计算机专业就业前景如何？",
        answer="计算机专业就业前景非常好，平均起薪15-25k，就业率超过90%。主要就业方向：后端、前端、算法、运维等。建议积累项目经验，刷LeetCode。",
        category="就业",
        keywords="计算机,就业,薪资"
    )
    print(result)
    
    result = await insert_knowledge(
        question="如何准备字节跳动面试？",
        answer="字节跳动面试注重算法能力，LeetCode中等难度常见。流程：简历->笔试->2-3轮技术面->HR面。建议刷LeetCode150题以上，准备项目经历。",
        category="面试",
        keywords="字节跳动,面试,算法"
    )
    print(result)

    result = await insert_knowledge(
        question="杭州和深圳哪个地方互联网公司多？",
        answer="深圳互联网公司更多，尤其是大型科技公司如腾讯、华为等总部在深圳。杭州以阿里巴巴为代表，也有很多互联网公司，但整体数量和规模不如深圳。",
        category="城市",
        keywords="杭州,深圳,互联网公司"
    )
    print(result)
    
    print("\n" + "=" * 60)
    print("3. 知识库统计")
    print("=" * 60)
    result = await get_stats()
    print(result)
    
    print("\n" + "=" * 60)
    print("4. 搜索：算法面试怎么准备")
    print("=" * 60)
    result = await search_knowledge("算法面试怎么准备", top_k=2)
    print(result)
    
    print("\n" + "=" * 60)
    print("5. 搜索：计算机专业薪资")
    print("=" * 60)
    result = await search_knowledge("计算机专业工资多少", top_k=2)
    print(result)

if __name__ == "__main__":
    asyncio.run(test())
