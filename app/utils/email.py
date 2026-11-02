import resend

from app.config.settings import settings
from app.schemas.order import OrderRead


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


# Envía la confirmación de compra con la boleta PDF adjunta
def send_order_confirmation_email(
    to_email: str, order: OrderRead, pdf_bytes: bytes
) -> None:
    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send(
        {
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": f"Confirmación de tu compra N° {order.id:06d} - GameVault UCN",
            "html": (
                "<p>¡Gracias por tu compra en GameVault UCN!</p>"
                f"<p>Total pagado: ${order.total_amount:,.2f}</p>"
                "<p>Adjuntamos tu boleta en PDF.</p>"
            ),
            # Resend recibe el archivo como lista de bytes
            "attachments": [
                {
                    "filename": f"boleta-{order.id:06d}.pdf",
                    "content": list(pdf_bytes),
                }
            ],
        }
    )
