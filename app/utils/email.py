import httpx
import random
from typing import Optional

class QQEmailService:
    """使用QQ邮箱SMTP发送邮件（通过第三方邮件服务）"""
    
    def __init__(self, api_key: str, from_email: str):
        self.api_key = api_key
        self.from_email = from_email
    
    @staticmethod
    def generate_code(length: int = 6) -> str:
        """生成6位数字验证码"""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])
    

    async def send_verification_code_smtp(self, to_email: str, code: str) -> bool:
        """
        使用SMTP直接发送（需要QQ邮箱的SMTP授权码）
        更简单，不需要第三方服务
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # QQ邮箱SMTP配置
        smtp_host = "smtp.qq.com"
        smtp_port = 465
        smtp_user = self.from_email  # 例如：your-email@qq.com
        smtp_password = self.api_key  # QQ邮箱的授权码（不是密码）
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = "【职业规划智能体】邮箱验证码"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>欢迎使用职业规划智能体</h2>
            <p>您正在进行邮箱验证，验证码如下：</p>
            <div style="font-size: 32px; font-weight: bold; color: #232334; 
                        background: #f5f5f5; padding: 20px; text-align: center; 
                        letter-spacing: 5px; border-radius: 8px; margin: 20px 0;">
                {code}
            </div>
            <p>验证码有效期为 <strong>5分钟</strong>，请勿泄露给他人。</p>
            <p>如果这不是您本人的操作，请忽略此邮件。</p>
            <hr style="margin: 30px 0;">
            <p style="color: #999; font-size: 12px;">此邮件由系统自动发送，请勿回复</p>
        </div>
        """
        
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        try:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"发送邮件失败: {e}")
            return False