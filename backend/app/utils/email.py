"""Email sending utility (SMTP)."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an HTML email. Returns True on success, False on failure."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(f"Email not configured — skipping send to {to_email}: {subject}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"MedicalRAG <{settings.EMAIL_FROM}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())

        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email send failed to {to_email}: {e}")
        return False


def build_verification_email(
    username: str, token: str, base_url: str = "http://localhost:3000"
) -> str:
    verify_url = f"{base_url}/auth/verify?token={token}"
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #00c8d0; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
        <h1 style="color: white; margin: 0;">⚕️ MedicalRAG</h1>
      </div>
      <div style="padding: 30px; background: #f9f9f9;">
        <h2>Hello {username}!</h2>
        <p>Please verify your email address to activate your account.</p>
        <a href="{verify_url}" style="background: #00c8d0; color: white; padding: 12px 24px;
           border-radius: 6px; text-decoration: none; display: inline-block; margin: 20px 0;">
          Verify Email Address
        </a>
        <p style="color: #666; font-size: 14px;">
          Link expires in 24 hours. If you didn't register, please ignore this email.
        </p>
      </div>
    </div>
    """


def build_password_reset_email(
    username: str, token: str, base_url: str = "http://localhost:3000"
) -> str:
    reset_url = f"{base_url}/auth/reset-password?token={token}"
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #00c8d0; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
        <h1 style="color: white; margin: 0;">⚕️ MedicalRAG</h1>
      </div>
      <div style="padding: 30px; background: #f9f9f9;">
        <h2>Password Reset Request</h2>
        <p>Hello {username}, we received a request to reset your password.</p>
        <a href="{reset_url}" style="background: #00c8d0; color: white; padding: 12px 24px;
           border-radius: 6px; text-decoration: none; display: inline-block; margin: 20px 0;">
          Reset Password
        </a>
        <p style="color: #666; font-size: 14px;">
          Link expires in 24 hours. If you didn't request this, ignore this email — your password is unchanged.
        </p>
      </div>
    </div>
    """
