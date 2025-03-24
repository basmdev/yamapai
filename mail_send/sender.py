import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


def send_email(file_path):
    """Отправка письма с вложением."""
    sender_email = config.SENDER_EMAIL
    receiver_email = config.RECEIVER_EMAIL
    smtp_server = config.SMTP_SERVER
    smtp_port = config.SMTP_PORT
    smtp_user = config.SMTP_USER
    smtp_password = config.SMTP_PASS
    subject = f"Отчет за {datetime.now().strftime('%d.%m.%Y')}"
    body = "Проверка выполнена сервисом YamapAI"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    attachment = open(file_path, "rb")
    part = MIMEBase("application", "octet-stream")
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition", f'attachment; filename={file_path.split("report_")[1]}'
    )
    msg.attach(part)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print("Письмо успешно отправлено")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
