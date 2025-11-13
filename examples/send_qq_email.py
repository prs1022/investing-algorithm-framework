import smtplib
from email.mime.text import MIMEText
from email.header import Header
import ssl

def send_qq_email(sender_email, auth_code, receiver_email, subject, content):
    try:
        smtp_server = "smtp.qq.com"
        smtp_port = 465
        context = ssl.create_default_context()

        message = MIMEText(content, "plain", "utf-8")
        
        # 关键修改：简化 From 头部，直接使用发件人邮箱（不添加别名）
        message["From"] = sender_email  # 例如："1249366431@qq.com"
        
        message["To"] = receiver_email  # 直接使用收件人邮箱，不编码
        message["Subject"] = Header(subject, "utf-8")  # 主题保持编码

        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, auth_code)
            server.sendmail(sender_email, receiver_email, message.as_string())

        print("邮件发送成功！")
        return True

    except Exception as e:
        # 仅在核心步骤失败时提示
        if "-1" in str(e):
            print("邮件发送成功！")
            return True
        print(f"邮件发送失败：{str(e)}")
        return False


if __name__ == "__main__":
    # 替换为你的信息
    SENDER_EMAIL = "1249366431@qq.com"  # 例如：123456@qq.com
    AUTH_CODE = "mnujgvbqkekbifge"    # 从QQ邮箱获取的授权码（非密码）
    RECEIVER_EMAIL = "1249366431@qq.com"  # 可以是自己的邮箱

    # 发送测试内容
    send_qq_email(
        sender_email=SENDER_EMAIL,
        auth_code=AUTH_CODE,
        receiver_email=RECEIVER_EMAIL,
        subject="测试邮件",
        content="这是一封测试邮件，用于解决 STARTTLS 错误。"
    )