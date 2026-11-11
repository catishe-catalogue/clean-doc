from email.message import EmailMessage

import aiosmtplib
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class EmailService:
    async def send_magic_code(self, to_email: str, code: str, magic_link_url: str) -> None:
        """Отправляет транзакционное письмо с кодом и ссылкой входа."""
        msg = EmailMessage()
        msg["Subject"] = f"{code} — ваш код для входа в сервис «Чистый документ»"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email

        plain_text = (
            f"Здравствуйте!\n\n"
            f"Ваш одноразовый код для входа в сервис «Чистый документ»: {code}\n"
            f"Код действителен в течение 15 минут.\n\n"
            f"Или перейдите по прямой ссылке для быстрого входа:\n"
            f"{magic_link_url}\n\n"
            f"Если вы не запрашивали этот код, просто проигнорируйте письмо."
        )

        html_text = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; padding: 24px;">
          <div style="max-width: 520px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <h2 style="color: #0f172a; margin-top: 0; font-size: 22px;">Вход в «Чистый документ»</h2>
            <p style="color: #475569; font-size: 15px; line-height: 1.5;">Используйте данный код для входа в сервис и управления вашими документами:</p>
            <div style="background-color: #f1f5f9; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0;">
              <span style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #2563eb;">{code}</span>
            </div>
            <p style="color: #64748b; font-size: 13px; text-align: center;">Код действует 15 минут. Никому его не сообщайте.</p>
            <div style="text-align: center; margin-top: 24px;">
              <a href="{magic_link_url}" style="display: inline-block; background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 500; font-size: 14px;">Войти в один клик</a>
            </div>
          </div>
        </body>
        </html>
        """

        msg.set_content(plain_text)
        msg.add_alternative(html_text, subtype="html")

        logger.info("email_sending_started", to_domain=to_email.split("@")[-1])

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=settings.SMTP_USE_TLS,
            username=settings.SMTP_USER if settings.SMTP_USER else None,
            password=settings.SMTP_PASSWORD if settings.SMTP_PASSWORD else None,
        )
        logger.info("email_sending_success")


email_service = EmailService()
