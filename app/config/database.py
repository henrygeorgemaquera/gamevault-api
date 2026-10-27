from typing import Generator
from sqlmodel import SQLModel, Session, create_engine

from app.config.settings import settings
import app.models # Para registrar las tablas

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Crea las tablas en SQLModel
def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)

# Inyección de dependencia: abre la sesión
def get_db() -> Generator[Session, None, None]:
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()
