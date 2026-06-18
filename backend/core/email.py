import smtplib
import logging
from email.message import EmailMessage
from core.config import settings

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, html_content: str):
    """
    Sends an email using the SMTP settings configured in .env.
    This function is synchronous and should be called via BackgroundTasks in FastAPI.
    """
    if not settings.SMTP_SERVER or not settings.SMTP_USER:
        logger.warning("SMTP settings not configured. Email not sent.")
        logger.info(f"Subject: {subject}\nTo: {to_email}\nBody: {html_content}")
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg['To'] = to_email
    msg.set_content("Por favor, activa el HTML para ver este correo.")
    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent successfully to {to_email}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")

def send_welcome_email(email_to: str):
    """Sends a welcome email upon registration."""
    subject = "¡Bienvenido a Value Betting AI!"
    html_content = f"""
    <html>
    <body>
        <h2>¡Hola!</h2>
        <p>Gracias por registrarte en <b>Value Betting AI</b>.</p>
        <p>Estamos encantados de tenerte con nosotros. Accede a tu panel para ver las mejores combinadas y predicciones de valor.</p>
        <p>Un saludo,<br/>El equipo de Value Betting AI</p>
    </body>
    </html>
    """
    send_email(email_to, subject, html_content)

def send_reset_password_email(email_to: str, token: str):
    """Sends a password reset email with a temporary token."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "Restablece tu contraseña - Value Betting AI"
    html_content = f"""
    <html>
    <body>
        <h2>Solicitud de restablecimiento de contraseña</h2>
        <p>Hemos recibido una solicitud para cambiar tu contraseña.</p>
        <p>Haz clic en el siguiente enlace para establecer una nueva contraseña (este enlace caducará en 1 hora):</p>
        <p><a href="{reset_url}" style="padding: 10px 20px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 5px;">Restablecer contraseña</a></p>
        <p>Si no has solicitado este cambio, puedes ignorar este correo.</p>
        <p>Un saludo,<br/>El equipo de Value Betting AI</p>
    </body>
    </html>
    """
    send_email(email_to, subject, html_content)
