from langchain_core.tools import tool
import json

@tool
async def get_job_market_info(major: str, city: str = "全国") -> str:
    """
    获取指定专业在特定城市的就业市场信息。
    
    参数:
        major: 专业名称，如"计算机科学与技术"、"金融学"等
        city: 城市名称，默认为"全国"
    
    返回:
        包含薪资、就业率、主要行业等的就业信息
    """
    # 模拟数据（实际使用时替换为真实API）
    market_data = {
        "计算机科学与技术": {
            "全国": {
                "salary": "15-25k",
                "rate": "92%",
                "industries": ["互联网", "金融科技", "国企IT"],
                "description": "就业前景广阔，薪资待遇好"
            },
            "北京": {
                "salary": "18-30k",
                "rate": "94%",
                "industries": ["互联网大厂", "金融IT", "人工智能"],
                "description": "大厂集中，机会多"
            },
            "上海": {
                "salary": "17-28k",
                "rate": "93%",
                "industries": ["金融科技", "互联网", "外企"],
                "description": "金融和互联网并重"
            },
            "深圳": {
                "salary": "18-28k",
                "rate": "95%",
                "industries": ["硬件科技", "互联网", "通信"],
                "description": "科技公司聚集地"
            }
        },
        "金融学": {
            "全国": {
                "salary": "10-20k",
                "rate": "85%",
                "industries": ["银行", "证券", "基金"],
                "description": "稳定但竞争激烈"
            },
            "上海": {
                "salary": "15-25k",
                "rate": "88%",
                "industries": ["投行", "基金", "信托"],
                "description": "金融中心，高端岗位多"
            },
            "北京": {
                "salary": "14-24k",
                "rate": "87%",
                "industries": ["银行总部", "券商", "监管机构"],
                "description": "总部经济，稳定性好"
            }
        }
    }
    
    if major not in market_data:
        return json.dumps({
            "error": True,
            "message": f"暂时没有{major}专业的详细就业数据",
            "suggestion": "建议查看教育部官方就业报告或学校就业指导中心"
        }, ensure_ascii=False)
    
    city_data = market_data[major].get(city, market_data[major]["全国"])
    
    return json.dumps({
        "error": False,
        "major": major,
        "city": city,
        "salary": city_data["salary"],
        "employment_rate": city_data["rate"],
        "industries": city_data["industries"],
        "description": city_data["description"]
    }, ensure_ascii=False)
