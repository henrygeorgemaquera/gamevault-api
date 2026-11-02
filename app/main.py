import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from sqlmodel import Session

from app.config.database import create_db_and_tables, engine
from app.config.settings import settings
from app.routers import admin, auth, cart, catalog, orders, reviews, wishlist
from app.schemas.error import ErrorResponse
from app.utils.cloudinary_client import is_cloudinary_configured
from app.utils.exceptions import register_exception_handlers
from app.utils.jobs import shutdown_scheduler, start_scheduler
from app.utils.logger import setup_logging
from app.utils.rate_limit import limiter
from seed import run_seed

setup_logging()
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    create_db_and_tables()
    run_seed()
    start_scheduler()
    logger.info("Entorno GameVault UCN iniciado correctamente")
    yield
    shutdown_scheduler()
    logger.info("Entorno GameVault UCN detenido correctamente")


app = FastAPI(
    title="GameVault UCN API",
    description="API REST para la plataforma de distribución de videojuegos GameVault UCN.",
    version="1.0.0",
    lifespan=lifespan,
    responses={
        400: {"model": ErrorResponse, "description": "Solicitud inválida"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
        403: {"model": ErrorResponse, "description": "Acceso denegado"},
        404: {"model": ErrorResponse, "description": "Recurso no encontrado"},
        409: {"model": ErrorResponse, "description": "Conflicto de estado"},
        422: {"model": ErrorResponse, "description": "Error de validación"},
        429: {"model": ErrorResponse, "description": "Límite de peticiones excedido"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"},
    },
)

app.state.limiter = limiter
register_exception_handlers(app)


@app.get("/health", tags=["Calidad y Entorno"])
def health_check():
    """Verifica el estado operativo de la API, base de datos y servicios externos."""
    with Session(engine) as db:
        db.exec(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "connected",
        "email": "resend" if settings.RESEND_API_KEY else "unconfigured",
        "cloudinary": "cloudinary" if is_cloudinary_configured() else "dev-local",
    }


app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(wishlist.router)
app.include_router(reviews.router)
app.include_router(admin.router)
