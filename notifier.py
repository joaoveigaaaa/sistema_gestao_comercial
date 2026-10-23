import logging
import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def enviar_email_relatorio(caminho_pdf, destinatarios, assunto="Relatório de Inteligência Comercial",
                           corpo=None):
    servidor = os.getenv("SMTP_SERVER")
    porta = int(os.getenv("SMTP_PORT", 587))
    usuario = os.getenv("SMTP_USER")
    senha = os.getenv("SMTP_PASSWORD")
    if not (servidor and usuario and senha):
        raise RuntimeError("SMTP_SERVER, SMTP_USER e SMTP_PASSWORD precisam estar no .env")

    msg = EmailMessage()
    msg["From"] = usuario
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = assunto
    msg.set_content(corpo or "Prezados,\n\nSegue em anexo o Relatório de Inteligência Comercial.\n\n"
                              "Atenciosamente,\nEquipe de TI")

    with open(caminho_pdf, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf",
                           filename=os.path.basename(caminho_pdf))

    with smtplib.SMTP(servidor, porta, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(usuario, senha)
        smtp.send_message(msg)

    logging.info(f"E-mail enviado para: {', '.join(destinatarios)}")