import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(
    sender_email,
    receiver_email,
    subject,
    body,
    file_path,
    smtp_server,
    smtp_port,
    smtp_user,
    smtp_password,
):
    """Отправка письма с вложением."""
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
        "Content-Disposition", f'attachment; filename={file_path.split("/")[-1]}'
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


sender_email = "mail@gmail.com"
receiver_email = "mail@gmail.com"
subject = "Тема письма"
body = "Текст письма"
file_path = "./reports/report.xlsx"
smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_user = "mail@gmail.com"
smtp_password = "cifxjtvbuzzajhxu"

send_email(
    sender_email,
    receiver_email,
    subject,
    body,
    file_path,
    smtp_server,
    smtp_port,
    smtp_user,
    smtp_password,
)
