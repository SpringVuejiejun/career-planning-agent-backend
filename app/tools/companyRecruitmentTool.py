from langchain_core.tools import tool
import json

@tool
async def get_company_recruitment(company_name: str, job_type: str = "校招") -> str:
    """
    查询特定公司的校招/实习信息。
    
    参数:
        company_name: 公司名称，如"字节跳动"、"腾讯"
        job_type: 职位类型，可选"实习"、"校招"，默认为"校招"
    
    返回:
        该公司的招聘信息和申请建议
    """
    companies_data = {
        "字节跳动": {
            "校招": {
                "time": "8-10月（秋招），3-4月（春招补录）",
                "key_points": ["非常注重算法能力", "项目深度追问", "技术栈灵活"],
                "interviews": ["LeetCode中等/困难", "系统设计", "项目深挖"],
                "positions": ["后端", "前端", "算法", "客户端", "测开", "产品"],
                "locations": ["北京", "上海", "深圳", "杭州", "广州"],
                "tips": ["刷LeetCode150题以上", "准备项目难点和优化思路", "关注官方招聘号"]
            },
            "实习": {
                "time": "全年可投，暑期实习机会最多",
                "key_points": ["转正机会大", "面试难度略低于校招", "看重基础"],
                "interviews": ["LeetCode简单/中等", "基础知识", "项目经验"],
                "positions": ["技术岗为主", "产品岗", "运营岗"],
                "locations": ["北京", "上海", "深圳"],
                "tips": ["提前3-6个月准备", "争取内推", "实习经历很重要"]
            }
        },
        "腾讯": {
            "校招": {
                "time": "8-10月（秋招），3-4月（春招）",
                "key_points": ["注重计算机基础", "C++/Go技术栈", "重视项目"],
                "interviews": ["操作系统", "网络", "算法", "项目"],
                "positions": ["后端", "客户端", "游戏开发", "产品"],
                "locations": ["深圳", "北京", "上海", "广州", "成都"],
                "tips": ["加强C++", "准备网络和操作系统", "有开源经历加分"]
            }
        },
        "阿里巴巴": {
            "校招": {
                "time": "7-9月（秋招），3-4月（春招）",
                "key_points": ["Java技术栈", "重视中间件", "看重项目"],
                "interviews": ["Java基础", "JVM", "并发", "框架源码"],
                "positions": ["后端", "前端", "算法", "测试"],
                "locations": ["杭州", "北京", "上海", "深圳"],
                "tips": ["精通Java", "研究Spring源码", "有高并发经验加分"]
            }
        }
    }
    
    if company_name not in companies_data:
        return json.dumps({
            "error": True,
            "message": f"暂时没有{company_name}的详细招聘信息",
            "suggestion": "建议关注公司官网招聘页面或牛客网"
        }, ensure_ascii=False)
    
    company = companies_data[company_name]
    info = company.get(job_type, company.get("校招", {}))
    
    return json.dumps({
        "error": False,
        "company": company_name,
        "job_type": job_type,
        "recruitment_time": info.get("time", "关注官方通知"),
        "key_points": info.get("key_points", []),
        "interview_focus": info.get("interviews", []),
        "positions": info.get("positions", []),
        "locations": info.get("locations", []),
        "tips": info.get("tips", [])
    }, ensure_ascii=False)
