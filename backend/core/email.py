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
    # --- Diagnostic logging (visible in HF logs) ---
    logger.info(f"📧 [email] Attempting to send email to: {to_email}")
    logger.info(f"📧 [email] SMTP_SERVER='{settings.SMTP_SERVER}' SMTP_PORT={settings.SMTP_PORT} SMTP_USER='{settings.SMTP_USER}' PASSWORD_SET={'yes' if settings.SMTP_PASSWORD else 'NO'}")

    if not settings.SMTP_SERVER or not settings.SMTP_USER:
        logger.warning("⚠️ [email] SMTP_SERVER or SMTP_USER is empty — email NOT sent. Check Hugging Face Secrets.")
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg['To'] = to_email
    msg.set_content("Por favor, activa el HTML para ver este correo.")
    msg.add_alternative(html_content, subtype='html')

    try:
        logger.info(f"📧 [email] Connecting to SMTP {settings.SMTP_SERVER}:{settings.SMTP_PORT}...")
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"✅ [email] Email sent successfully to {to_email}: {subject}")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ [email] Authentication failed for {settings.SMTP_USER}. Check SMTP_PASSWORD. Error: {e}")
    except smtplib.SMTPConnectError as e:
        logger.error(f"❌ [email] Cannot connect to SMTP server {settings.SMTP_SERVER}:{settings.SMTP_PORT}. Error: {e}")
    except Exception as e:
        logger.error(f"❌ [email] Failed to send email to {to_email}: {type(e).__name__}: {e}")

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
