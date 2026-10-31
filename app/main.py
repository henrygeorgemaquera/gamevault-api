from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config.database import create_db_and_tables
from app.config.settings import settings
from app.routers import auth, catalog
from app.utils.jobs import shutdown_scheduler, start_scheduler
from app.utils.rate_limit import limiter
from seed import run_seed


# Lo que va antes del yield corre al iniciar y lo de después al apagar
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
    version="0.2.0",
    lifespan=lifespan,
)

# Conecta slowapi y responde 429 cuando se pasan del límite
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(catalog.router)
