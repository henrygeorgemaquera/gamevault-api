import resend

from app.config.settings import settings


# Envía el código por Resend; si falla lanza excepción y el service la maneja
def send_verification_email(to_email: str, code: str) -> None:
    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send(
        {
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": "Tu código de verificación - GameVault UCN",
            "html": (
                "<p>Tu código de verificación es:</p>"
                f"<h2>{code}</h2>"
                f"<p>Expira en {settings.VERIFICATION_CODE_EXPIRE_MINUTES} minutos.</p>"
            ),
        }
    )
