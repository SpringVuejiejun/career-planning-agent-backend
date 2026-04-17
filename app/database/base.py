from sqlalchemy.orm import declarative_base

# 创建基类
Base = declarative_base()

# 导入所有模型，确保create_all能创建表
from app.models.user import User
from app.models.chat import ChatConversation, ChatMessage