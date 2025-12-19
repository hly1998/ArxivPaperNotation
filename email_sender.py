"""
邮件发送模块 - 发送论文摘要邮件
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import markdown


class EmailSender:
    """邮件发送器"""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int = 587,
        sender_email: str = "",
        password: str = "",
        use_ssl: bool = False
    ):
        """
        初始化邮件发送器
        
        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            sender_email: 发送方邮箱
            password: 邮箱密码或授权码
            use_ssl: 是否使用SSL（端口465使用SSL，587使用STARTTLS）
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.password = password
        self.use_ssl = use_ssl or smtp_port == 465
    
    def _markdown_to_html(self, md_content: str) -> str:
        """将Markdown转换为HTML"""
        # 使用markdown库转换
        html = markdown.markdown(
            md_content,
            extensions=['tables', 'fenced_code', 'nl2br']
        )
        
        # 添加基本样式
        styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 20px 0;
        }}
        blockquote {{
            background-color: #ecf0f1;
            border-left: 4px solid #3498db;
            padding: 10px 15px;
            margin: 10px 0;
            color: #666;
        }}
        strong {{
            color: #2c3e50;
        }}
        .paper-section {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
{html}
</body>
</html>
"""
        return styled_html
    
    def send_email(
        self,
        recipients: List[str],
        subject: str,
        content: str,
        is_markdown: bool = True
    ) -> bool:
        """
        发送邮件
        
        Args:
            recipients: 收件人列表
            subject: 邮件主题
            content: 邮件内容（Markdown或纯文本）
            is_markdown: 内容是否为Markdown格式
        
        Returns:
            是否发送成功
        """
        if not all([self.smtp_server, self.sender_email, self.password, recipients]):
            print("❌ 邮件配置不完整")
            return False
        
        try:
            # 创建邮件
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = ", ".join(recipients)
            
            # 纯文本版本
            text_part = MIMEText(content, "plain", "utf-8")
            message.attach(text_part)
            
            # HTML版本（如果是Markdown）
            if is_markdown:
                html_content = self._markdown_to_html(content)
                html_part = MIMEText(html_content, "html", "utf-8")
                message.attach(html_part)
            
            # 发送邮件
            server = None
            try:
                if self.use_ssl:
                    # SSL连接
                    context = ssl.create_default_context()
                    server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
                else:
                    # STARTTLS连接
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                    server.starttls()
                
                server.login(self.sender_email, self.password)
                server.sendmail(self.sender_email, recipients, message.as_string())
                print(f"✅ 邮件发送成功，收件人: {', '.join(recipients)}")
                return True
            finally:
                # 安全关闭连接（忽略关闭时的错误，QQ邮箱常见问题）
                if server:
                    try:
                        server.quit()
                    except Exception:
                        pass  # 忽略关闭连接时的错误
            
        except smtplib.SMTPAuthenticationError:
            print("❌ 邮箱认证失败，请检查用户名和密码/授权码")
            return False
        except smtplib.SMTPException as e:
            print(f"❌ SMTP错误: {e}")
            return False
        except Exception as e:
            print(f"❌ 发送邮件失败: {e}")
            return False


def send_paper_digest(
    smtp_server: str,
    smtp_port: int,
    sender_email: str,
    password: str,
    recipients: List[str],
    digest_content: str,
    date: str
) -> bool:
    """
    发送论文摘要邮件
    
    Args:
        smtp_server: SMTP服务器
        smtp_port: SMTP端口
        sender_email: 发送方邮箱
        password: 密码
        recipients: 收件人列表
        digest_content: 摘要内容（Markdown格式）
        date: 日期
    
    Returns:
        是否发送成功
    """
    sender = EmailSender(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        sender_email=sender_email,
        password=password
    )
    
    subject = f"📚 arXiv论文日报 - {date}"
    
    return sender.send_email(
        recipients=recipients,
        subject=subject,
        content=digest_content,
        is_markdown=True
    )

