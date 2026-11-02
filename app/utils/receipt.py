from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

from app.schemas.order import OrderRead


# Genera la boleta en PDF (en memoria) con el detalle guardado del pedido
def build_receipt_pdf(order: OrderRead, buyer_email: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    story = [
        Paragraph("GameVault UCN - Boleta de compra", styles["Title"]),
        Paragraph(f"Boleta N° {order.id:06d}", styles["Normal"]),
        Paragraph(f"Fecha: {order.created_at:%d/%m/%Y %H:%M} UTC", styles["Normal"]),
        Paragraph(f"Cliente: {buyer_email}", styles["Normal"]),
        Spacer(1, 20),
    ]

    # Tabla con un renglón por título y el total al final
    rows = [["Título", "Precio", "Descuento", "Total"]]
    for item in order.items:
        rows.append(
            [
                item.title,
                f"${item.unit_price:,.2f}",
                f"{item.discount_percent}%",
                f"${item.final_price:,.2f}",
            ]
        )
    rows.append(["", "", "TOTAL", f"${order.total_amount:,.2f}"])
    story.append(Table(rows, style=[("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))

    doc.build(story)
    return buffer.getvalue()
