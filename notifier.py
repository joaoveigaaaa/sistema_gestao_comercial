import os 
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

def enviar_email_relatorio(caminho_pdf, destinatarios, assunto="Relatório de Inteligência Comercial"):
    SMTP_SERVER= os.getenv("SMTP_SERVER")
    SMTP_PORT= int(os.getenv("SMTP_PORT", 587))
    SMTP_USER= os.getenv
    SMTP_PASSWORD= os.getenv("SMTP_PASSWORD")

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(destinatarios)
    msg['Subject'] = assunto

    corpo_email = "Prezados,\n\nSegue em anexo o Relatório de Inteligência Comercial.\n\nAtenciosamente,\nEquipe de TI"
    msg.attach(MIMEText(corpo_email, 'plain'))

    with open(caminho_pdf, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(caminho_pdf))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(caminho_pdf)}"'
        msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, destinatarios, msg.as_string())

    print(f"Email enviado com sucesso para: {', '.join(destinatarios)}")