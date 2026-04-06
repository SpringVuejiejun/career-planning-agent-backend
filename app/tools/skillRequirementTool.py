from langchain_core.tools import tool
import json

@tool
async def get_skill_requirements(job_title: str) -> str:
    """
    获取特定职位所需的技能要求。
    
    参数:
        job_title: 职位名称，如"前端开发工程师"、"产品经理"等
    
    返回:
        该职位的技能要求、学习路径和建议
    """
    skills_data = {
        "后端开发工程师": {
            "core_skills": ["Java/Go/Python", "数据库", "Linux", "分布式系统"],
            "learning_path": ["语言基础(1-2月)", "框架学习(2-3月)", "项目实战(2-3月)"],
            "salary_range": "20-35k",
            "difficulty": "较高"
        },
        "前端开发工程师": {
            "core_skills": ["HTML/CSS/JS", "React/Vue", "构建工具", "浏览器原理"],
            "learning_path": ["基础三件套(2-3月)", "框架进阶(2-3月)", "工程化(1-2月)"],
            "salary_range": "18-30k",
            "difficulty": "中等"
        },
        "算法工程师": {
            "core_skills": ["Python", "机器学习", "深度学习", "数据结构"],
            "learning_path": ["数学基础(2-3月)", "ML/DL算法(3-4月)", "论文复现(2-3月)"],
            "salary_range": "25-45k",
            "difficulty": "高"
        },
        "产品经理": {
            "core_skills": ["用户研究", "原型设计", "数据分析", "沟通协调"],
            "learning_path": ["产品思维(1-2月)", "工具使用(1月)", "实战项目(2-3月)"],
            "salary_range": "15-30k",
            "difficulty": "中等"
        }
    }
    
    if job_title not in skills_data:
        return json.dumps({
            "error": True,
            "message": f"暂时没有{job_title}的详细技能要求",
            "suggestion": "建议查看招聘网站或行业报告"
        }, ensure_ascii=False)
    
    data = skills_data[job_title]
    return json.dumps({
        "error": False,
        "job_title": job_title,
        "core_skills": data["core_skills"],
        "learning_path": data["learning_path"],
        "salary_range": data["salary_range"],
        "difficulty": data["difficulty"]
    }, ensure_ascii=False)
