from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config.database import create_db_and_tables
from app.config.settings import settings
from app.routers import admin, auth, cart, catalog, orders, reviews, wishlist
from app.utils.jobs import shutdown_scheduler, start_scheduler
from app.utils.rate_limit import limiter
from seed import run_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    create_db_and_tables()
    run_seed()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="GameVault UCN API",
    description="API REST para la plataforma de distribución de videojuegos GameVault UCN.",
    version="0.3.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(wishlist.router)
app.include_router(reviews.router)
app.include_router(admin.router)
