from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
from typing import Optional, Tuple
import random

from app.models.user import User
from app.utils.redis_client import get_redis
from app.utils.security import create_access_token
from app.utils.email import QQEmailService

class AuthService:
    def __init__(self, db: AsyncSession, email_service: QQEmailService):
        self.db = db
        self.email_service = email_service
    
    async def send_verification_code(self, email: str) -> Tuple[bool, str]:
        """
        发送验证码
        返回: (是否成功, 消息)
        """
        redis = await get_redis()
        
        # 检查发送频率（60秒内不能重复发送）
        rate_limit_key = f"email:rate:{email}"
        ttl = await redis.ttl(rate_limit_key)
        if ttl > 0:
            return False, f"请等待 {ttl} 秒后再试"
        
        # 生成6位验证码
        code = self.email_service.generate_code()
        
        # 存储到Redis，有效期5分钟
        code_key = f"email:code:{email}"
        await redis.setex(code_key, 300, code)  # 5分钟
        
        # 设置频率限制（60秒）
        await redis.setex(rate_limit_key, 60, "1")
        
        # 发送邮件
        success = await self.email_service.send_verification_code_smtp(email, code)
        
        if success:
            return True, "验证码已发送"
        else:
            # 发送失败，删除已存储的验证码
            await redis.delete(code_key)
            return False, "邮件发送失败，请稍后重试"
    
    async def verify_and_login(self, email: str, code: str, username: Optional[str] = None) -> Tuple[Optional[str], bool, str]:
        """
        验证验证码并登录/注册
        返回: (token, is_new_user, error_message)
        """
        redis = await get_redis()
        
        # 1. 验证验证码
        code_key = f"email:code:{email}"
        stored_code = await redis.get(code_key)
        
        if not stored_code:
            return None, False, "验证码已过期，请重新发送"
        
        if stored_code != code:
            return None, False, "验证码错误"
        
        # 验证成功，删除验证码（防止重复使用）
        await redis.delete(code_key)
        
        # 2. 查找或创建用户
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        is_new_user = False
        if not user:
            # 新用户注册
            is_new_user = True
            
            # 生成默认用户名（从邮箱提取）
            default_username = email.split('@')[0]
            
            # 如果提供了自定义用户名，使用它
            final_username = username if username else default_username
            
            user = User(
                email=email,
                username=final_username,
                last_login=datetime.utcnow()
            )
            self.db.add(user)
        else:
            # 老用户更新最后登录时间
            user.last_login = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)
        
        # 3. 生成JWT Token
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        
        return access_token, is_new_user, ""
    
    async def get_user_info(self, user_id: int) -> Optional[User]:
        """获取用户信息"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def update_username(self, user_id: int, new_username: str) -> bool:
        """更新用户名"""
        result = await self.db.execute(
            select(User).where(User.username == new_username)
        )
        if result.scalar_one_or_none():
            return False  # 用户名已存在
        
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(username=new_username)
        )
        await self.db.commit()
        return True