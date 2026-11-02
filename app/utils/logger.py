import contextvars
import logging
import sys
from datetime import datetime, timezone

# Variable de contexto para asociar cada log con el request_id de la petición actual
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestIdFilter(logging.Filter):
    """Inyecta el request_id actual en cada registro de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("-")
        return True


class StructuredFormatter(logging.Formatter):
    """Formato estructurado consistente para auditoría de eventos, errores y seguridad."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(
            record.created, tz=timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        req_id = getattr(record, "request_id", "-")
        base = (
            f"timestamp={timestamp} | level={record.levelname} | "
            f"request_id={req_id} | logger={record.name} | "
            f"message={record.getMessage()}"
        )
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            return f"{base}\n{exc_text}"
        return base


def setup_logging() -> None:
    """Configura el logging estructurado en consola y archivo para toda la aplicación."""
    root_logger = logging.getLogger("app")
    root_logger.setLevel(logging.INFO)
    root_logger.propagate = False

    if root_logger.handlers:
        return

    formatter = StructuredFormatter()
    req_filter = RequestIdFilter()

    # Salida en consola (terminal de uvicorn)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(req_filter)

    # Salida en archivo local de auditoría
    file_handler = logging.FileHandler("gamevault.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(req_filter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
