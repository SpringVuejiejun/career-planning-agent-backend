from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class SendCodeRequest(BaseModel):
    email: EmailStr = Field(..., description="QQ邮箱地址")

class VerifyCodeRequest(BaseModel):
    email: EmailStr = Field(..., description="邮箱地址")
    code: str = Field(..., min_length=6, max_length=6, description="6位验证码")
    username: Optional[str] = Field(None, min_length=1, max_length=50, description="可选，首次登录时设置的用户名")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    is_new_user: bool  # 是否是新注册用户

class UserInfoResponse(BaseModel):
    id: int
    email: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True