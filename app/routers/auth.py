from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database.session import get_db
from app.schemas.auth import SendCodeRequest, VerifyCodeRequest, TokenResponse, UserInfoResponse
from app.services.auth_service import AuthService
from app.utils.email import QQEmailService
from app.dependencies.auth import get_current_user
from app.models.user import User
import os

router = APIRouter(prefix="/auth", tags=["认证"])


# 使用QQ邮箱SMTP（推荐，免费）
email_service = QQEmailService(
    api_key=os.getenv("QQ_EMAIL_AUTH_CODE"),  # QQ邮箱授权码
    from_email=os.getenv("QQ_EMAIL", "3205814035@qq.com")  # 你的QQ邮箱
)


@router.post("/send-code", status_code=status.HTTP_200_OK)
async def send_verification_code(
    request: SendCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """发送验证码到指定邮箱"""
    service = AuthService(db, email_service)
    success, message = await service.send_verification_code(request.email)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, "email": request.email}


@router.post("/login", response_model=TokenResponse)
async def login_with_code(
    request: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """验证验证码并登录/注册"""
    service = AuthService(db, email_service)
    token, is_new_user, error = await service.verify_and_login(
        request.email, 
        request.code,
        request.username
    )
    
    if not token:
        raise HTTPException(status_code=400, detail=error)
    
    return TokenResponse(
        access_token=token,
        expires_in=30 * 24 * 60 * 60,  # 30天
        is_new_user=is_new_user
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前登录用户信息"""
    return current_user


@router.put("/username")
async def update_username(
    username: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户名"""
    service = AuthService(db, email_service)
    success = await service.update_username(current_user.id, username)
    
    if not success:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    return {"message": "用户名更新成功"}