import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    async def send_verification_email(email: str, token: str) -> None:
        """
        Sends an email verification link to the user.
        In a production environment, this should connect to an SMTP server.
        For development, if SMTP is not configured, we print to console.
        """
        verify_url = f"{settings.CORS_ORIGINS.split(',')[0]}/auth/verify-email?token={token}"
        subject = "Verify your MedicalRAG Account"
        body = f"Welcome to MedicalRAG!\n\nPlease verify your email by clicking the link below:\n{verify_url}"
        
        await EmailService._send_email(email, subject, body)

    @staticmethod
    async def send_password_reset_email(email: str, token: str) -> None:
        """
        Sends a password reset link to the user.
        """
        reset_url = f"{settings.CORS_ORIGINS.split(',')[0]}/auth/reset-password?token={token}"
        subject = "Reset your MedicalRAG Password"
        body = f"You requested a password reset.\n\nPlease reset your password by clicking the link below:\n{reset_url}\n\nIf you did not request this, please ignore this email."
        
        await EmailService._send_email(email, subject, body)

    @staticmethod
    async def _send_email(to_email: str, subject: str, body: str) -> None:
        """
        Core function to send an email. 
        Logs to console if SMTP_USER is not configured.
        """
        if not settings.SMTP_USER:
            # Development mode: mock email sending
            logger.info("=" * 60)
            logger.info(f"MOCK EMAIL TO: {to_email}")
            logger.info(f"SUBJECT: {subject}")
            logger.info(f"BODY:\n{body}")
            logger.info("=" * 60)
            return

        # Production mode: Actual SMTP logic would go here
        try:
            import aiosmtplib
            from email.message import EmailMessage

            message = EmailMessage()
            message["From"] = settings.EMAIL_FROM
            message["To"] = to_email
            message["Subject"] = subject
            message.set_content(body)

            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=(settings.SMTP_PORT == 465),
                start_tls=(settings.SMTP_PORT == 587),
            )
            logger.info(f"Successfully sent email to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
