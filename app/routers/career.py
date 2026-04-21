import json
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.career import (
    JobProfile,
    JobRelation,
    StudentCapabilityProfile,
    CareerDevelopmentReport,
    ReportExportArtifact,
)
from app.models.user import User
from app.services.career_service import (
    ensure_seed_job_data,
    build_student_profile_from_text,
    build_report_for_student,
    to_markdown_export,
)
from app.utils.resume_extract import extract_text_from_upload

router = APIRouter(prefix="/career", tags=["职业画像"])


class JobProfileOut(BaseModel):
    id: int
    code: str
    name: str
    category: Optional[str] = None
    level: Optional[str] = None
    description: Optional[str] = None
    skills: Optional[Any] = None
    certificates: Optional[Any] = None
    competencies: Optional[Any] = None
    internship: Optional[Any] = None
    other_requirements: Optional[Any] = None

    class Config:
        from_attributes = True


class JobRelationOut(BaseModel):
    id: int
    relation_type: str
    from_job_id: int
    to_job_id: int
    title: Optional[str] = None
    rationale: Optional[str] = None
    requirements_gap: Optional[Any] = None

    class Config:
        from_attributes = True


class JobGraphResponse(BaseModel):
    jobs: list[JobProfileOut]
    relations: list[JobRelationOut]


class StudentProfileCreateManual(BaseModel):
    text: str = Field(..., min_length=10, description="学生录入信息/简历文本")


class StudentProfileOut(BaseModel):
    id: int
    source_type: str
    source_filename: Optional[str] = None
    skills: Optional[Any] = None
    certificates: Optional[Any] = None
    competencies: Optional[Any] = None
    internship: Optional[Any] = None
    projects: Optional[Any] = None
    education: Optional[Any] = None
    awards: Optional[Any] = None
    completeness_score: Optional[int] = None
    competitiveness_score: Optional[int] = None
    scoring_detail: Optional[Any] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReportCreateRequest(BaseModel):
    student_profile_id: int
    target_job_id: int
    intention: Optional[str] = Field(None, description="个人意愿/约束，例如城市/方向偏好")


class ReportOut(BaseModel):
    id: int
    title: str
    status: str
    content_markdown: str
    content_json: Optional[Any] = None
    match_summary: Optional[Any] = None
    overall_match_score: Optional[int] = None
    action_plan: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReportUpdateRequest(BaseModel):
    title: Optional[str] = None
    content_markdown: Optional[str] = None
    status: Optional[str] = Field(None, description="draft|finalized")


@router.post("/seed")
async def seed_job_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 允许普通用户也可触发（MVP）；如需仅管理员，后续加 role 限制
    await ensure_seed_job_data(db)
    return {"message": "seed ok"}


@router.get("/jobs", response_model=list[JobProfileOut])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category: Optional[str] = None,
):
    await ensure_seed_job_data(db)
    stmt = select(JobProfile).order_by(JobProfile.category.asc().nulls_last(), JobProfile.name.asc())
    if category:
        stmt = stmt.where(JobProfile.category == category)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/jobs/{job_id}", response_model=JobProfileOut)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await ensure_seed_job_data(db)
    row = (await db.execute(select(JobProfile).where(JobProfile.id == job_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return row


@router.get("/graph", response_model=JobGraphResponse)
async def get_job_graph(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    relation_type: Optional[str] = None,  # vertical|transition|None(all)
):
    await ensure_seed_job_data(db)
    jobs = (await db.execute(select(JobProfile))).scalars().all()
    rel_stmt = select(JobRelation)
    if relation_type:
        rel_stmt = rel_stmt.where(JobRelation.relation_type == relation_type)
    relations = (await db.execute(rel_stmt)).scalars().all()
    return JobGraphResponse(jobs=jobs, relations=relations)


@router.post("/student-profiles/manual", response_model=StudentProfileOut)
async def create_student_profile_manual(
    body: StudentProfileCreateManual,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await build_student_profile_from_text(
        db=db,
        user_id=current_user.id,
        source_type="manual",
        source_text=body.text,
        source_filename=None,
    )
    return profile


@router.post("/student-profiles/resume", response_model=StudentProfileOut)
async def create_student_profile_resume_upload(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
    text_hint: Optional[str] = Form(None),
):
    raw = await file.read()
    extracted, method = extract_text_from_upload(file.filename, file.content_type, raw)
    merged = (text_hint or "").strip()
    if extracted.strip():
        merged = f"{merged}\n\n{extracted}".strip()
    if len(merged) < 10:
        scanned_hint = "（该 PDF 可能是扫描件图片版，通常没有可提取的文本层）" if "no_text_layer" in method else ""
        raise HTTPException(
            status_code=400,
            detail=f"简历内容为空或无法解析（类型：{method}）{scanned_hint}。请上传 txt/pdf/docx，或粘贴文本到补充说明。",
        )

    profile = await build_student_profile_from_text(
        db=db,
        user_id=current_user.id,
        source_type="resume_upload",
        source_text=merged,
        source_filename=file.filename,
    )
    return profile


@router.get("/student-profiles", response_model=list[StudentProfileOut])
async def list_student_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(StudentCapabilityProfile)
        .where(StudentCapabilityProfile.user_id == current_user.id)
        .order_by(StudentCapabilityProfile.created_at.desc())
        .limit(50)
    )
    return (await db.execute(stmt)).scalars().all()


@router.get("/student-profiles/{profile_id}", response_model=StudentProfileOut)
async def get_student_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        await db.execute(
            select(StudentCapabilityProfile).where(
                StudentCapabilityProfile.id == profile_id,
                StudentCapabilityProfile.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="画像不存在")
    return row


@router.post("/reports", response_model=ReportOut)
async def create_report(
    body: ReportCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await ensure_seed_job_data(db)
    report = await build_report_for_student(
        db=db,
        user_id=current_user.id,
        student_profile_id=body.student_profile_id,
        target_job_id=body.target_job_id,
        intention=body.intention,
    )
    return report


@router.get("/reports", response_model=list[ReportOut])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(CareerDevelopmentReport)
        .where(CareerDevelopmentReport.user_id == current_user.id)
        .order_by(CareerDevelopmentReport.created_at.desc())
        .limit(50)
    )
    return (await db.execute(stmt)).scalars().all()


@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        await db.execute(
            select(CareerDevelopmentReport).where(
                CareerDevelopmentReport.id == report_id,
                CareerDevelopmentReport.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="报告不存在")
    return row


@router.put("/reports/{report_id}", response_model=ReportOut)
async def update_report(
    report_id: int,
    body: ReportUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        await db.execute(
            select(CareerDevelopmentReport).where(
                CareerDevelopmentReport.id == report_id,
                CareerDevelopmentReport.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="报告不存在")
    if body.title is not None:
        row.title = body.title[:200]
    if body.content_markdown is not None:
        row.content_markdown = body.content_markdown
    if body.status is not None:
        if body.status not in ("draft", "finalized"):
            raise HTTPException(status_code=400, detail="status 必须为 draft|finalized")
        row.status = body.status
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return row


@router.post("/reports/{report_id}/polish", response_model=ReportOut)
async def polish_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        await db.execute(
            select(CareerDevelopmentReport).where(
                CareerDevelopmentReport.id == report_id,
                CareerDevelopmentReport.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="报告不存在")

    # MVP：直接复用生成逻辑的“润色”，让 LLM 根据现有 markdown 进行优化与完整性检查
    polished_md = await to_markdown_export(row.content_markdown, mode="polish")
    row.content_markdown = polished_md
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/reports/{report_id}/export")
async def export_report(
    report_id: int,
    fmt: str = "markdown",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        await db.execute(
            select(CareerDevelopmentReport).where(
                CareerDevelopmentReport.id == report_id,
                CareerDevelopmentReport.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="报告不存在")

    if fmt not in ("txt", "md", "html"):
        raise HTTPException(status_code=400, detail="fmt 仅支持 txt|md|html")

    mode = "markdown" if fmt == "txt" else fmt
    exported = await to_markdown_export(row.content_markdown, mode=mode)
    artifact = ReportExportArtifact(
        report_id=row.id,
        export_format=fmt,
        artifact_text=exported,
        artifact_meta={"generated_at": datetime.utcnow().isoformat()},
    )
    db.add(artifact)
    await db.commit()
    return {"format": fmt, "content": exported}
