from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from fastapi import Depends
from sqlmodel import Session, col, delete, select

from app.config.database import get_db
from app.models.user import User


# 1. EL CONTRATO: lo que el service puede pedirle al repositorio
class IUserRepository(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    def save(self, user: User) -> User: ...

    @abstractmethod
    def delete_unverified_created_before(self, cutoff: datetime) -> int: ...


# 2. LA IMPLEMENTACIÓN con SQLModel
class UserRepository(IUserRepository):
    def __init__(self, db: Session):
        self.db = db

    # Consulta parametrizada por el ORM (sin concatenar SQL)
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.exec(select(User).where(User.email == email)).first()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.get(User, user_id)

    # Sirve tanto para crear como para actualizar
    def save(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    # Usado por el job: borra cuentas sin verificar creadas antes de la fecha límite
    def delete_unverified_created_before(self, cutoff: datetime) -> int:
        result = self.db.exec(
            delete(User).where(col(User.is_verified).is_(False), col(User.created_at) < cutoff)
        )
        self.db.commit()
        return result.rowcount


# Aquí se elige la implementación concreta que recibe el service
def get_user_repository(db: Session = Depends(get_db)) -> IUserRepository:
    return UserRepository(db)
