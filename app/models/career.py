from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database.base import Base


class JobProfile(Base):
    """
    就业岗位画像（可扩展 JSON 化）
    """

    __tablename__ = "job_profiles"
    __table_args__ = (
        UniqueConstraint("code", name="uq_job_profiles_code"),
        Index("idx_job_profiles_category_level", "category", "level"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    code = Column(String(80), nullable=False, index=True)  # 稳定标识：例如 UI_DESIGNER
    name = Column(String(120), nullable=False, index=True)
    category = Column(String(120), nullable=True, index=True)  # 方向/职类
    level = Column(String(50), nullable=True, index=True)  # junior/mid/senior/lead/...
    description = Column(Text, nullable=True)

    # 画像要求（均为 JSON，便于迭代）
    skills = Column(JSON, nullable=True)  # 专业技能要求列表/结构
    certificates = Column(JSON, nullable=True)  # 证书要求
    competencies = Column(JSON, nullable=True)  # 通用能力：创新/学习/抗压/沟通/...
    internship = Column(JSON, nullable=True)  # 实习/项目经验要求
    other_requirements = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class JobRelation(Base):
    """
    岗位关系图谱：
    - vertical：晋升/垂直发展
    - transition：换岗/可迁移
    """

    __tablename__ = "job_relations"
    __table_args__ = (
        Index("idx_job_relations_type_from", "relation_type", "from_job_id"),
        Index("idx_job_relations_type_to", "relation_type", "to_job_id"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    relation_type = Column(String(30), nullable=False, index=True)  # vertical | transition
    from_job_id = Column(BigInteger, ForeignKey("job_profiles.id", ondelete="CASCADE"), nullable=False)
    to_job_id = Column(BigInteger, ForeignKey("job_profiles.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=True)  # 关系标题：例如 “晋升到/可转岗到”
    rationale = Column(Text, nullable=True)  # 关系依据/说明
    requirements_gap = Column(JSON, nullable=True)  # 迁移差距（技能/证书/能力）

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StudentCapabilityProfile(Base):
    """
    学生就业能力画像（由录入/简历解析生成）
    """

    __tablename__ = "student_capability_profiles"
    __table_args__ = (
        Index("idx_student_profiles_user_created", "user_id", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    source_type = Column(String(30), nullable=False, default="manual")  # manual | resume_upload
    source_text = Column(Text, nullable=True)  # 原始录入文本/简历提取文本（MVP 先存文本）
    source_filename = Column(String(260), nullable=True)

    # 画像结构化结果
    skills = Column(JSON, nullable=True)
    certificates = Column(JSON, nullable=True)
    competencies = Column(JSON, nullable=True)
    internship = Column(JSON, nullable=True)
    projects = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)
    awards = Column(JSON, nullable=True)

    completeness_score = Column(Integer, nullable=True)  # 0-100
    competitiveness_score = Column(Integer, nullable=True)  # 0-100
    scoring_detail = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class CareerDevelopmentReport(Base):
    """
    学生职业生涯发展报告（可编辑、可导出）
    """

    __tablename__ = "career_development_reports"
    __table_args__ = (
        Index("idx_reports_user_created", "user_id", "created_at"),
        Index("idx_reports_profile_job", "student_profile_id", "target_job_id"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student_profile_id = Column(
        BigInteger,
        ForeignKey("student_capability_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_job_id = Column(
        BigInteger,
        ForeignKey("job_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(String(200), nullable=False, default="职业生涯发展报告")
    status = Column(String(30), nullable=False, default="draft")  # draft | finalized

    # 报告内容（编辑/润色/导出以此为准）
    content_markdown = Column(Text, nullable=False, default="")
    content_json = Column(JSON, nullable=True)  # 可选：结构化报告段落

    # 人岗匹配分析（量化差距）
    match_summary = Column(JSON, nullable=True)  # 各维度匹配度/差距
    overall_match_score = Column(Integer, nullable=True)  # 0-100

    # 行动计划
    action_plan = Column(JSON, nullable=True)  # short_term/mid_term + 指标/周期

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class ReportExportArtifact(Base):
    """
    导出产物/版本记录（MVP：存 markdown/HTML 或导出元数据）
    """

    __tablename__ = "report_export_artifacts"
    __table_args__ = (
        Index("idx_export_report_created", "report_id", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    report_id = Column(BigInteger, ForeignKey("career_development_reports.id", ondelete="CASCADE"), nullable=False)
    export_format = Column(String(30), nullable=False, default="markdown")  # markdown | html | pdf(meta)
    artifact_text = Column(Text, nullable=True)  # MVP：直接存文本
    artifact_meta = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
