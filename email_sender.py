"""
邮件发送模块 - 发送论文摘要邮件
"""
import smtplib
import ssl
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
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
        """将Markdown转换为HTML，生成简洁大气的邮件样式"""
        # 使用markdown库转换
        html = markdown.markdown(
            md_content,
            extensions=['tables', 'fenced_code', 'nl2br']
        )
        
        # 简洁大气的样式
        styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* 基础样式 */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            line-height: 1.75;
            color: #333;
            max-width: 780px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f8f9fa;
        }}
        
        /* 主容器 */
        .container {{
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        
        /* 内容区域 */
        .content {{
            padding: 36px 40px;
        }}
        
        /* 主标题 */
        h1 {{
            color: #1a1a1a;
            font-size: 24px;
            font-weight: 600;
            margin: 0 0 24px 0;
            padding-bottom: 16px;
            border-bottom: 2px solid #0066cc;
        }}
        
        /* 二级标题 */
        h2 {{
            color: #1a1a1a;
            font-size: 18px;
            font-weight: 600;
            margin: 32px 0 16px 0;
            padding-left: 12px;
            border-left: 3px solid #0066cc;
        }}
        
        /* 三级标题 - 论文标题 */
        h3 {{
            color: #0066cc;
            font-size: 16px;
            font-weight: 600;
            margin: 28px 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid #eee;
        }}
        
        /* 段落 */
        p {{
            margin: 10px 0;
            color: #444;
            font-size: 15px;
        }}
        
        strong {{
            color: #1a1a1a;
        }}
        
        /* 链接 */
        a {{
            color: #0066cc;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        /* 分隔线 */
        hr {{
            border: none;
            height: 1px;
            background: #e5e5e5;
            margin: 28px 0;
        }}
        
        /* 表格 */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 14px;
        }}
        
        th {{
            background: #f5f5f5;
            color: #333;
            font-weight: 600;
            padding: 12px 10px;
            text-align: left;
            border-bottom: 2px solid #ddd;
        }}
        
        td {{
            padding: 10px;
            border-bottom: 1px solid #eee;
            color: #555;
        }}
        
        tr:hover td {{
            background: #fafafa;
        }}
        
        /* 引用块 */
        blockquote {{
            background: #f9f9f9;
            border-left: 3px solid #0066cc;
            padding: 12px 16px;
            margin: 16px 0;
            color: #555;
        }}
        
        /* 代码 */
        code {{
            background: #f0f0f0;
            color: #c7254e;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 13px;
            font-family: Consolas, Monaco, monospace;
        }}
        
        /* 列表 */
        ul, ol {{
            padding-left: 20px;
            margin: 12px 0;
        }}
        
        li {{
            margin: 6px 0;
            color: #444;
        }}
        
        /* 页脚 */
        .footer {{
            text-align: center;
            padding: 16px 20px;
            background: #fafafa;
            color: #999;
            font-size: 12px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
{html}
        </div>
        <div class="footer">
            ArXiv 论文通知系统 · 自动生成
        </div>
    </div>
</body>
</html>
"""
        return styled_html
    
    def send_email(
        self,
        recipients: List[str],
        subject: str,
        content: str,
        is_markdown: bool = True,
        max_retries: int = 3
    ) -> bool:
        """
        发送邮件（带重试机制）
        
        Args:
            recipients: 收件人列表
            subject: 邮件主题
            content: 邮件内容（Markdown或纯文本）
            is_markdown: 内容是否为Markdown格式
            max_retries: 最大重试次数
        
        Returns:
            是否发送成功
        """
        if not all([self.smtp_server, self.sender_email, self.password, recipients]):
            print("❌ 邮件配置不完整")
            return False
        
        # 创建邮件（在重试循环外创建，避免重复工作）
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
        
        # 重试发送
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                server = None
                try:
                    if self.use_ssl:
                        # SSL连接
                        context = ssl.create_default_context()
                        server = smtplib.SMTP_SSL(
                            self.smtp_server, 
                            self.smtp_port, 
                            context=context,
                            timeout=30  # 30秒超时
                        )
                    else:
                        # STARTTLS连接
                        server = smtplib.SMTP(
                            self.smtp_server, 
                            self.smtp_port,
                            timeout=30  # 30秒超时
                        )
                        server.starttls()
                    
                    server.login(self.sender_email, self.password)
                    server.sendmail(self.sender_email, recipients, message.as_string())
                    print(f"✅ 邮件发送成功，收件人: {', '.join(recipients)}")
                    return True
                finally:
                    # 安全关闭连接
                    if server:
                        try:
                            server.quit()
                        except Exception:
                            pass
                
            except smtplib.SMTPAuthenticationError:
                print("❌ 邮箱认证失败，请检查用户名和密码/授权码")
                return False  # 认证失败不重试
            except (smtplib.SMTPException, OSError, ConnectionError) as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = attempt * 5  # 递增等待时间
                    print(f"⚠️ 发送失败 (尝试 {attempt}/{max_retries}): {e}")
                    print(f"   等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ SMTP错误: {e}")
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = attempt * 5
                    print(f"⚠️ 发送失败 (尝试 {attempt}/{max_retries}): {e}")
                    print(f"   等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ 发送邮件失败: {e}")
        
        return False


def send_paper_digest(
    smtp_server: str,
    smtp_port: int,
    sender_email: str,
    password: str,
    recipients: List[str],
    digest_content: str,
    date: str,
    use_ssl: bool = False
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
        use_ssl: 是否使用SSL（端口465用True，端口587用False）
    
    Returns:
        是否发送成功
    """
    sender = EmailSender(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        sender_email=sender_email,
        password=password,
        use_ssl=use_ssl
    )
    
    subject = f"arXiv论文日报 - {date}"
    
    return sender.send_email(
        recipients=recipients,
        subject=subject,
        content=digest_content,
        is_markdown=True
    )

