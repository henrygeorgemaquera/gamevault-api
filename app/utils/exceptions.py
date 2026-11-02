import logging
import uuid
from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.logger import request_id_ctx

logger = logging.getLogger("app.exceptions")

STATUS_CODE_MAP = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "validation_error",
    status.HTTP_423_LOCKED: "locked",
    status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_error",
    status.HTTP_502_BAD_GATEWAY: "bad_gateway",
}


def _build_error_payload(
    code: str,
    message: str,
    request_id: str,
    details: Optional[Any] = None,
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "detail": message,
        "request_id": request_id,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = req_id
        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        req_id = getattr(
            request.state, "request_id", request_id_ctx.get("-")
        )
        code = STATUS_CODE_MAP.get(exc.status_code, f"http_{exc.status_code}")
        message = (
            exc.detail
            if isinstance(exc.detail, str)
            else "Error en la solicitud"
        )
        details = None if isinstance(exc.detail, str) else exc.detail

        # Logging estructurado según severidad y tipo de evento
        client_ip = request.client.host if request.client else "unknown"
        if exc.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_423_LOCKED,
        ):
            logger.warning(
                "Acceso denegado: status=%s, code=%s, path=%s %s, ip=%s, motivo=%s",
                exc.status_code,
                code,
                request.method,
                request.url.path,
                client_ip,
                message,
            )
        elif exc.status_code >= 500:
            logger.error(
                "Error de servidor controlado: status=%s, path=%s %s, motivo=%s",
                exc.status_code,
                request.method,
                request.url.path,
                message,
            )
        else:
            logger.info(
                "Error de negocio controlado: status=%s, code=%s, path=%s %s, motivo=%s",
                exc.status_code,
                code,
                request.method,
                request.url.path,
                message,
            )

        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_payload(code, message, req_id, details),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        req_id = getattr(
            request.state, "request_id", request_id_ctx.get("-")
        )
        # jsonable_encoder evita que objetos ValueError dentro de ctx disparen un 500
        encoded_errors = jsonable_encoder(
            exc.errors(),
            custom_encoder={Exception: lambda e: str(e)},
        )
        logger.info(
            "Validación de entrada fallida (422): path=%s %s, errores=%s",
            request.method,
            request.url.path,
            len(encoded_errors),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_build_error_payload(
                code="validation_error",
                message="Datos de entrada inválidos.",
                request_id=req_id,
                details=encoded_errors,
            ),
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exception_handler(
        request: Request, exc: RateLimitExceeded
    ) -> JSONResponse:
        req_id = getattr(
            request.state, "request_id", request_id_ctx.get("-")
        )
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "Límite de peticiones excedido (429): path=%s %s, ip=%s, limite=%s",
            request.method,
            request.url.path,
            client_ip,
            exc.detail,
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=_build_error_payload(
                code="rate_limited",
                message="Demasiadas solicitudes. Intenta de nuevo más tarde.",
                request_id=req_id,
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        req_id = getattr(
            request.state, "request_id", request_id_ctx.get("-")
        )
        logger.exception(
            "Error crítico de base de datos: path=%s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_build_error_payload(
                code="internal_error",
                message="Error interno al procesar la operación en la base de datos.",
                request_id=req_id,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        req_id = getattr(
            request.state, "request_id", request_id_ctx.get("-")
        )
        logger.exception(
            "Excepción no controlada (500): path=%s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_build_error_payload(
                code="internal_error",
                message="Ocurrió un error interno inesperado.",
                request_id=req_id,
            ),
        )
