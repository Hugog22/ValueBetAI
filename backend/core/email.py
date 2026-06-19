import logging
import httpx
from core.config import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to_email: str, subject: str, html_content: str):
    """
    Sends an email using the Brevo (Sendinblue) API via HTTPS.
    This bypasses SMTP entirely (which is blocked on Hugging Face Spaces).
    Should be called via BackgroundTasks in FastAPI.
    """
    logger.info(f"📧 [email] Attempting to send email to: {to_email}")
    logger.info(f"📧 [email] BREVO_API_KEY set: {'yes' if settings.BREVO_API_KEY else 'NO'}")
    logger.info(f"📧 [email] FROM: {settings.EMAILS_FROM_EMAIL} ({settings.EMAILS_FROM_NAME})")

    if not settings.BREVO_API_KEY:
        logger.warning("⚠️ [email] BREVO_API_KEY is empty — email NOT sent. Add it as a Hugging Face Secret.")
        return

    payload = {
        "sender": {
            "name": settings.EMAILS_FROM_NAME,
            "email": settings.EMAILS_FROM_EMAIL,
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }

    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }

    try:
        response = httpx.post(BREVO_API_URL, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        logger.info(f"✅ [email] Email sent successfully to {to_email}: {subject}")
    except httpx.HTTPStatusError as e:
        logger.error(
            f"❌ [email] Brevo API error {e.response.status_code}: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"❌ [email] Failed to send email to {to_email}: {type(e).__name__}: {e}")


def send_welcome_email(email_to: str):
    """Sends a welcome email upon registration."""
    subject = "¡Bienvenido a Value Betting AI!"
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 30px;">
        <div style="max-width: 500px; margin: auto; background: white; border-radius: 10px; padding: 30px;">
            <h2 style="color: #064E3B;">¡Bienvenido/a a Value Betting AI! 🎉</h2>
            <p>Hola,</p>
            <p>Gracias por registrarte en <b>Value Betting AI</b>. Estamos encantados de tenerte con nosotros.</p>
            <p>Accede a tu panel para ver las mejores predicciones y apuestas de valor en tiempo real.</p>
            <br/>
            <p style="color: #888;">Un saludo,<br/><b>El equipo de Value Betting AI</b></p>
        </div>
    </body>
    </html>
    """
    send_email(email_to, subject, html_content)


def send_reset_password_email(email_to: str, token: str):
    """Sends a password reset email with a secure token link."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "Restablece tu contraseña - Value Betting AI"
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 30px;">
        <div style="max-width: 500px; margin: auto; background: white; border-radius: 10px; padding: 30px;">
            <h2 style="color: #064E3B;">Restablecimiento de contraseña</h2>
            <p>Hemos recibido una solicitud para restablecer la contraseña de tu cuenta.</p>
            <p>Haz clic en el botón de abajo para establecer una nueva contraseña. <b>Este enlace caducará en 1 hora.</b></p>
            <br/>
            <a href="{reset_url}" style="display: inline-block; padding: 12px 24px; background-color: #064E3B; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;">
                Restablecer contraseña
            </a>
            <br/><br/>
            <p style="color: #888; font-size: 13px;">Si no has solicitado este cambio, puedes ignorar este correo con total seguridad.</p>
            <p style="color: #888;">Un saludo,<br/><b>El equipo de Value Betting AI</b></p>
        </div>
    </body>
    </html>
    """
    send_email(email_to, subject, html_content)
