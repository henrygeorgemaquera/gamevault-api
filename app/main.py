from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config.database import create_db_and_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(
    title="GameVault UCN API",
    description="API REST para la plataforma de distribuciónn de videojuegos GameVault UCN.",
    version="0.1.0",
    lifespan=lifespan
)
