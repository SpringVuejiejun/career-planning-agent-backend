from langchain_core.tools import tool
import json

@tool
async def get_certificate_info(cert_name: str) -> str:
    """
    查询职业认证证书的相关信息。
    
    参数:
        cert_name: 证书名称，如"PMP"、"CPA"
    
    返回:
        证书的价值、考试要求
    """
    certs_data = {
        "PMP": {
            "full_name": "项目管理专业人士认证",
            "value": "国际认可，适合有经验的项目经理",
            "requirements": "35学时培训 + 考试经验",
            "cost": "约3900元",
            "difficulty": "中等",
            "time": "3-6个月准备"
        },
        "CPA": {
            "full_name": "注册会计师",
            "value": "国内含金量最高，财会领域必备",
            "requirements": "专科以上学历",
            "cost": "每科约70元",
            "difficulty": "高",
            "time": "2-3年"
        },
        "软考": {
            "full_name": "计算机技术与软件专业技术资格",
            "value": "国企事业单位认可，可评职称",
            "requirements": "无学历要求",
            "cost": "约200元",
            "difficulty": "中等",
            "time": "2-3个月"
        }
    }
    
    if cert_name not in certs_data:
        return json.dumps({
            "error": True,
            "message": f"暂时没有{cert_name}的详细信息",
            "suggestion": "建议查看官方考试网站"
        }, ensure_ascii=False)
    
    data = certs_data[cert_name]
    return json.dumps({
        "error": False,
        "cert_name": cert_name,
        "full_name": data["full_name"],
        "value": data["value"],
        "requirements": data["requirements"],
        "cost": data["cost"],
        "difficulty": data["difficulty"],
        "preparation_time": data["time"]
    }, ensure_ascii=False)
