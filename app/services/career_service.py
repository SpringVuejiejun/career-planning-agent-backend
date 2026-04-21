import json
import re
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import create_llm
from app.models.career import (
    JobProfile,
    JobRelation,
    StudentCapabilityProfile,
    CareerDevelopmentReport,
)


def _clamp_score(x: Any) -> Optional[int]:
    try:
        v = int(x)
    except Exception:
        return None
    return max(0, min(100, v))


def _safe_json_loads(text: str) -> Optional[dict]:
    text = (text or "").strip()
    if not text:
        return None
    # 兼容模型输出带 ```json ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # 取第一个 { ... } 块
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        text = m.group(0)
    try:
        return json.loads(text)
    except Exception:
        return None


def _strip_markdown_to_plain(text: str) -> str:
    """
    将常见 Markdown 语法尽量转换为纯文本结构，避免前端出现 # * - 等符号。
    """
    s = (text or "").strip()
    if not s:
        return ""
    s = re.sub(r"^```[\s\S]*?\n", "", s)  # 去掉 ```xxx 开头行
    s = s.replace("```", "")
    # 去掉标题符号
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.M)
    # 去掉常见列表符号
    s = re.sub(r"^\s*[-*+]\s+", "", s, flags=re.M)
    # 去掉强调符号
    s = s.replace("**", "").replace("__", "").replace("*", "")
    # 规整空行
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s


def _plain_to_markdown(plain: str) -> str:
    """
    把“纯文本结构报告”转换为 Markdown（导出用）。
    规则：
    - 标题：... -> # ...
    - 一、二、三、四 -> ## ...
    - 其他保持原样
    """
    s = _strip_markdown_to_plain(plain)
    if not s:
        return ""
    lines = s.splitlines()
    out: list[str] = []
    for line in lines:
        t = line.strip()
        if t.startswith("标题："):
            out.append("# " + t.replace("标题：", "", 1).strip())
            continue
        if re.match(r"^[一二三四五六七八九十]+、", t):
            out.append("## " + t)
            continue
        out.append(line)
    return "\n".join(out).strip()


async def ensure_seed_job_data(db: AsyncSession) -> None:
    exists = (await db.execute(select(JobProfile.id).limit(1))).scalar_one_or_none()
    if exists:
        return

    # >=10 个岗位画像（字段覆盖：技能/证书/创新/学习/抗压/沟通/实习等）
    jobs = [
        {
            "code": "UI_DESIGNER",
            "name": "UI/视觉设计师",
            "category": "设计",
            "level": "junior",
            "description": "负责产品界面视觉与交互呈现，输出设计规范与高保真稿。",
            "skills": ["Figma/Sketch", "设计规范/组件库", "版式与视觉基础", "交互基础", "可用性与易用性"],
            "certificates": ["（可选）Adobe 相关认证"],
            "competencies": {
                "创新能力": "能提出多套视觉方案并论证取舍",
                "学习能力": "快速掌握新组件/新设计趋势",
                "抗压能力": "迭代频繁时保持交付质量",
                "沟通能力": "与产品/研发对齐交互与实现边界",
            },
            "internship": ["有作品集/实习经历优先", "参与过 1-2 个完整产品设计闭环"],
        },
        {
            "code": "UX_DESIGNER",
            "name": "用户体验设计师",
            "category": "设计",
            "level": "mid",
            "description": "通过研究与数据分析优化产品体验，制定体验策略与流程。",
            "skills": ["用户研究", "信息架构", "交互设计", "可用性测试", "数据分析基础"],
            "certificates": ["（可选）用户研究/数据分析相关证书"],
            "competencies": {
                "创新能力": "从用户洞察提出体验策略",
                "学习能力": "掌握新研究方法/工具",
                "抗压能力": "在不确定需求下推进验证",
                "沟通能力": "跨部门推动体验落地",
            },
            "internship": ["有研究项目/可用性测试经验", "能输出研究报告与改进建议"],
        },
        {
            "code": "FRONTEND_ENGINEER",
            "name": "前端开发工程师",
            "category": "研发",
            "level": "junior",
            "description": "负责 Web 前端功能开发、性能优化与工程化落地。",
            "skills": ["JavaScript/TypeScript", "React/Vue", "HTTP/浏览器基础", "工程化/构建工具", "调试与性能"],
            "certificates": ["（可选）前端/云原生相关证书"],
            "competencies": {
                "创新能力": "在交互与性能上提出改进方案",
                "学习能力": "快速掌握新框架/组件库",
                "抗压能力": "在 deadline 下保证质量",
                "沟通能力": "与后端/产品对齐接口与需求",
            },
            "internship": ["至少 1 个中等复杂度项目/实习经历", "能独立完成模块交付"],
        },
        {
            "code": "BACKEND_ENGINEER",
            "name": "后端开发工程师",
            "category": "研发",
            "level": "junior",
            "description": "负责服务端接口、数据存储、性能与稳定性建设。",
            "skills": ["Python/Java/Go 其一", "数据库SQL", "缓存与消息队列基础", "接口设计", "日志/监控/排障"],
            "certificates": ["（可选）云/数据库/网络相关证书"],
            "competencies": {
                "创新能力": "在架构/性能上提出优化",
                "学习能力": "快速理解业务与系统",
                "抗压能力": "线上问题快速定位",
                "沟通能力": "与多方协作推进需求",
            },
            "internship": ["有服务端项目/实习", "理解基本工程实践（测试/CI）"],
        },
        {
            "code": "DATA_ANALYST",
            "name": "数据分析师",
            "category": "数据",
            "level": "junior",
            "description": "负责指标体系、数据分析与业务洞察输出。",
            "skills": ["SQL", "Excel/BI 工具", "统计学基础", "数据可视化", "业务理解"],
            "certificates": ["（可选）数据分析/统计相关证书"],
            "competencies": {
                "创新能力": "提出可验证的业务假设",
                "学习能力": "快速学习新指标与业务",
                "抗压能力": "频繁需求下保证结论准确",
                "沟通能力": "用业务语言解释数据结论",
            },
            "internship": ["做过指标分析/看板项目", "能输出结构化报告"],
        },
        {
            "code": "DATA_ENGINEER",
            "name": "数据工程师",
            "category": "数据",
            "level": "mid",
            "description": "负责数据采集、清洗、建模与数据平台管道建设。",
            "skills": ["ETL/ELT", "数据仓库建模", "Python/SQL", "任务调度", "数据质量"],
            "certificates": ["（可选）大数据平台相关证书"],
            "competencies": {
                "创新能力": "优化数据链路与成本",
                "学习能力": "掌握不同数据组件",
                "抗压能力": "数据延迟/故障快速恢复",
                "沟通能力": "与业务/分析对齐口径",
            },
            "internship": ["有数据管道/数仓项目经验", "熟悉至少一种调度/计算框架"],
        },
        {
            "code": "PRODUCT_MANAGER",
            "name": "产品经理",
            "category": "产品",
            "level": "junior",
            "description": "负责需求分析、方案设计、项目推进与结果复盘。",
            "skills": ["需求分析", "原型设计", "数据指标", "项目管理", "竞品分析"],
            "certificates": ["（可选）PMP/NPDP"],
            "competencies": {
                "创新能力": "基于洞察提出方案并验证",
                "学习能力": "快速理解业务与用户",
                "抗压能力": "多线推进与频繁变化",
                "沟通能力": "跨团队推进落地",
            },
            "internship": ["有完整项目推进经验", "能写 PRD 并跟进上线"],
        },
        {
            "code": "QA_ENGINEER",
            "name": "测试开发工程师",
            "category": "质量",
            "level": "junior",
            "description": "负责测试方案、自动化测试与质量平台建设。",
            "skills": ["测试基础", "自动化测试", "脚本语言", "CI/CD 基础", "缺陷管理"],
            "certificates": ["（可选）ISTQB"],
            "competencies": {
                "创新能力": "设计高覆盖的测试策略",
                "学习能力": "快速熟悉新业务",
                "抗压能力": "版本发布压力下保证质量",
                "沟通能力": "推动缺陷闭环",
            },
            "internship": ["参与过自动化/压测项目", "能独立完成测试用例设计"],
        },
        {
            "code": "AI_ENGINEER",
            "name": "AI/算法工程师",
            "category": "算法",
            "level": "junior",
            "description": "负责模型训练/推理、评估与工程化落地。",
            "skills": ["Python", "深度学习基础", "模型训练与评估", "数据处理", "工程化部署基础"],
            "certificates": ["（可选）机器学习/深度学习证书"],
            "competencies": {
                "创新能力": "提出改进思路并验证",
                "学习能力": "跟进论文/新模型",
                "抗压能力": "实验失败/迭代快速调整",
                "沟通能力": "向非算法同学解释方案与风险",
            },
            "internship": ["有竞赛/项目/实习经历", "具备复现实验与写报告能力"],
        },
        {
            "code": "OPERATIONS",
            "name": "运营专员",
            "category": "运营",
            "level": "junior",
            "description": "负责活动策划、内容运营、增长与用户维护。",
            "skills": ["内容策划", "用户运营", "数据分析基础", "活动执行", "增长基础"],
            "certificates": ["（可选）新媒体/数据分析证书"],
            "competencies": {
                "创新能力": "策划新玩法与增长策略",
                "学习能力": "快速理解产品与用户",
                "抗压能力": "高强度活动期保持执行",
                "沟通能力": "跨团队协作推进活动",
            },
            "internship": ["有活动/社群/内容运营经验", "能沉淀 SOP 与复盘"],
        },
    ]

    job_rows: list[JobProfile] = []
    for j in jobs:
        job_rows.append(
            JobProfile(
                code=j["code"],
                name=j["name"],
                category=j.get("category"),
                level=j.get("level"),
                description=j.get("description"),
                skills=j.get("skills"),
                certificates=j.get("certificates"),
                competencies=j.get("competencies"),
                internship=j.get("internship"),
                other_requirements=j.get("other_requirements"),
            )
        )
    db.add_all(job_rows)
    await db.flush()

    by_code = {row.code: row for row in job_rows}

    # 1) 垂直岗位图谱：晋升路径
    vertical_edges = [
        ("UI_DESIGNER", "UX_DESIGNER", "发展到体验设计", "从视觉/交互落地扩展到研究与体验策略"),
        ("FRONTEND_ENGINEER", "BACKEND_ENGINEER", "全栈发展方向", "增强服务端能力形成全栈竞争力"),
        ("DATA_ANALYST", "DATA_ENGINEER", "向数据工程拓展", "从分析走向数据资产与管道建设"),
        ("PRODUCT_MANAGER", "UX_DESIGNER", "产品向体验融合", "通过研究能力增强产品决策与体验"),
    ]

    # 2) 换岗路径图谱：至少 5 个岗位，每个不少于 2 条
    transition_paths = [
        ("UI_DESIGNER", "FRONTEND_ENGINEER", "转前端", "学习工程化与实现能力，能与设计协作落地"),
        ("UI_DESIGNER", "PRODUCT_MANAGER", "转产品", "强化需求分析与项目推进"),
        ("FRONTEND_ENGINEER", "QA_ENGINEER", "转测开", "强化质量意识与自动化测试"),
        ("FRONTEND_ENGINEER", "PRODUCT_MANAGER", "转产品", "补齐业务与需求能力"),
        ("BACKEND_ENGINEER", "DATA_ENGINEER", "转数据工程", "补齐数仓/ETL/调度"),
        ("BACKEND_ENGINEER", "AI_ENGINEER", "转算法工程", "补齐模型训练与评估"),
        ("DATA_ANALYST", "PRODUCT_MANAGER", "转产品", "把数据洞察转为方案与推进"),
        ("DATA_ANALYST", "AI_ENGINEER", "转算法", "补齐 ML 基础与工程实践"),
        ("OPERATIONS", "PRODUCT_MANAGER", "运营转产品", "补齐产品方法论与PRD"),
        ("OPERATIONS", "DATA_ANALYST", "运营转数据分析", "补齐 SQL/指标与分析"),
    ]

    relations: list[JobRelation] = []
    for a, b, title, rationale in vertical_edges:
        relations.append(
            JobRelation(
                relation_type="vertical",
                from_job_id=by_code[a].id,
                to_job_id=by_code[b].id,
                title=title,
                rationale=rationale,
            )
        )
    for a, b, title, rationale in transition_paths:
        relations.append(
            JobRelation(
                relation_type="transition",
                from_job_id=by_code[a].id,
                to_job_id=by_code[b].id,
                title=title,
                rationale=rationale,
                requirements_gap={
                    "建议补齐": ["核心技能差距", "项目/实习经历差距", "作品/案例呈现方式"],
                },
            )
        )
    db.add_all(relations)
    await db.commit()


async def build_student_profile_from_text(
    *,
    db: AsyncSession,
    user_id: int,
    source_type: str,
    source_text: str,
    source_filename: Optional[str],
) -> StudentCapabilityProfile:
    """
    使用 LLM 将输入拆解为能力画像 + 完整度/竞争力评分
    """
    llm = create_llm(streaming=False, temperature=0.2)
    prompt = f"""
你是职业规划系统的结构化信息抽取与评估模块。
请把用户提供的信息拆解为“学生就业能力画像”，并输出 JSON（只输出 JSON，不要多余文字）。

字段要求：
- skills: 专业技能（列表，尽量具体）
- certificates: 证书（列表）
- competencies: 通用能力（对象，包含：创新能力/学习能力/抗压能力/沟通能力，可补充其他）
- internship: 实习能力（对象，包含：实习经历概述/岗位/成果/时长等，未知则为空）
- projects: 项目经历（列表）
- education: 教育背景（对象）
- awards: 奖项/竞赛（列表）
- completeness_score: 0-100（信息完整度）
- competitiveness_score: 0-100（综合竞争力）
- scoring_detail: 对评分的分项依据（对象）

用户信息：
\"\"\"{source_text}\"\"\"
""".strip()

    msg = await llm.ainvoke(prompt)
    data = _safe_json_loads(getattr(msg, "content", "") or "")
    if not isinstance(data, dict):
        # 兜底：不依赖模型也能落库
        data = {
            "skills": [],
            "certificates": [],
            "competencies": {},
            "internship": {},
            "projects": [],
            "education": {},
            "awards": [],
            "completeness_score": 40,
            "competitiveness_score": 40,
            "scoring_detail": {"fallback": True},
        }

    profile = StudentCapabilityProfile(
        user_id=user_id,
        source_type=source_type,
        source_text=source_text,
        source_filename=source_filename,
        skills=data.get("skills"),
        certificates=data.get("certificates"),
        competencies=data.get("competencies"),
        internship=data.get("internship"),
        projects=data.get("projects"),
        education=data.get("education"),
        awards=data.get("awards"),
        completeness_score=_clamp_score(data.get("completeness_score")),
        competitiveness_score=_clamp_score(data.get("competitiveness_score")),
        scoring_detail=data.get("scoring_detail"),
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


def _score_match(student: dict, job: dict) -> dict:
    """
    简易人岗匹配（MVP）：规则评分，后续可用 LLM 进一步校准
    """
    student_skills = set((student.get("skills") or []) if isinstance(student.get("skills"), list) else [])
    job_skills = set((job.get("skills") or []) if isinstance(job.get("skills"), list) else [])
    overlap = len(student_skills & job_skills)
    total = max(1, len(job_skills))
    skill_match = int(overlap / total * 100)

    # 通用能力：先按字段是否存在进行粗估
    comp = student.get("competencies") or {}
    comp_keys = ["创新能力", "学习能力", "抗压能力", "沟通能力"]
    comp_present = sum(1 for k in comp_keys if comp.get(k))
    comp_match = int(comp_present / len(comp_keys) * 100)

    overall = int(skill_match * 0.6 + comp_match * 0.4)
    return {
        "dimensions": {
            "专业技能": {"match": skill_match, "gap": max(0, 100 - skill_match)},
            "通用素质": {"match": comp_match, "gap": max(0, 100 - comp_match)},
        },
        "overall": overall,
        "notes": {
            "skill_overlap": list(student_skills & job_skills)[:20],
            "skill_missing": list(job_skills - student_skills)[:20],
        },
    }


async def build_report_for_student(
    *,
    db: AsyncSession,
    user_id: int,
    student_profile_id: int,
    target_job_id: int,
    intention: Optional[str],
) -> CareerDevelopmentReport:
    profile = (
        await db.execute(
            select(StudentCapabilityProfile).where(
                StudentCapabilityProfile.id == student_profile_id,
                StudentCapabilityProfile.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if not profile:
        raise ValueError("student profile not found")

    job = (await db.execute(select(JobProfile).where(JobProfile.id == target_job_id))).scalar_one_or_none()
    if not job:
        raise ValueError("job profile not found")

    match = _score_match(
        {"skills": profile.skills, "competencies": profile.competencies},
        {"skills": job.skills, "competencies": job.competencies},
    )

    # 结合 LLM 生成“纯自然语言结构化”报告（可编辑）
    llm = create_llm(streaming=False, temperature=0.5)
    prompt = f"""
你是面向中国大学生的职业规划顾问。请根据“岗位画像”和“学生就业能力画像”生成《学生职业生涯发展报告》。

输出要求（非常重要）：
- 只输出纯文本（自然语言），不要输出 Markdown。
- 不要出现 "#", "*", "-", "```" 等 Markdown 符号。
- 使用清晰的“分节结构”，推荐格式如下（必须严格遵循）：

标题：学生职业生涯发展报告

一、职业探索与岗位匹配
（用自然语言说明匹配度与差距，必须包含：专业技能匹配、通用素质匹配，两项都要给出量化百分比与差距点）

二、职业目标设定与职业路径规划
（给出目标岗位与理由；给出垂直晋升路径 1 条；给出换岗路径 2 条，并说明每条路径的补齐重点）

三、行动计划与成果展示
（短期/中期两阶段，分别包含：学习路径、实践安排、评估周期与指标）

四、完整性检查与下一步补充材料
（列出缺失信息，并用“需补充：...”标注；不要胡编具体经历）

岗位画像：
{json.dumps({'name': job.name, 'category': job.category, 'level': job.level, 'description': job.description, 'skills': job.skills, 'certificates': job.certificates, 'competencies': job.competencies, 'internship': job.internship}, ensure_ascii=False)}

学生画像：
{json.dumps({'skills': profile.skills, 'certificates': profile.certificates, 'competencies': profile.competencies, 'internship': profile.internship, 'projects': profile.projects, 'education': profile.education, 'awards': profile.awards, 'completeness_score': profile.completeness_score, 'competitiveness_score': profile.competitiveness_score}, ensure_ascii=False)}

量化匹配结果：
{json.dumps(match, ensure_ascii=False)}

个人意愿/约束（可为空）：
{intention or ''}
""".strip()

    msg = await llm.ainvoke(prompt)
    plain = _strip_markdown_to_plain((getattr(msg, "content", "") or "").strip())
    if not plain:
        plain = "标题：学生职业生涯发展报告\n\n（生成失败，请稍后重试）"

    report = CareerDevelopmentReport(
        user_id=user_id,
        student_profile_id=student_profile_id,
        target_job_id=target_job_id,
        title=f"职业发展报告：{job.name}",
        status="draft",
        content_markdown=plain,
        content_json=None,
        match_summary=match.get("dimensions"),
        overall_match_score=match.get("overall"),
        action_plan=None,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def to_markdown_export(content_markdown: str, mode: str = "markdown") -> str:
    """
    导出/润色（MVP）：
    - markdown：原样返回
    - html：简单包裹
    - polish：LLM 做润色与完整性检查
    """
    if mode == "markdown":
        # txt 导出：纯文本结构
        return _strip_markdown_to_plain(content_markdown)
    if mode == "md":
        # md 导出：将纯文本结构转换为 markdown 标题
        return _plain_to_markdown(content_markdown)
    if mode == "html":
        plain = _strip_markdown_to_plain(content_markdown)
        body = (
            plain.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        # 使用 <pre> 保留换行与缩进
        return f"<!doctype html><html><head><meta charset='utf-8'/></head><body><pre style='white-space:pre-wrap;font-family:system-ui'>{body}</pre></body></html>"
    if mode == "polish":
        llm = create_llm(streaming=False, temperature=0.3)
        prompt = f"""
你是职业规划报告编辑助手。请对下列“纯文本结构的职业规划报告”进行：
- 语言润色（更专业、清晰）
- 内容完整性检查（如缺少关键项则补充合理建议）
- 不要胡编具体经历；对于未知信息用“需补充：...”标注

输出要求（非常重要）：
- 只输出纯文本（自然语言），不要输出 Markdown。
- 不要出现 "#", "*", "-", "```" 等 Markdown 符号。
- 保持四个章节结构（“一、二、三、四”），并保证内容更完整可执行。

原报告：
\"\"\"{content_markdown}\"\"\"
""".strip()
        msg = await llm.ainvoke(prompt)
        out = _strip_markdown_to_plain((getattr(msg, "content", "") or "").strip())
        return out or _strip_markdown_to_plain(content_markdown)
    return content_markdown
