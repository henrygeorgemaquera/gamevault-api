import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    # EmailStr valida el formato del correo
    email: EmailStr
    password: str

    # Revisa que la contraseña sea fuerte
    @field_validator("password")
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        # bcrypt solo soporta hasta 72 bytes
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar los 72 bytes")
        if not re.search(r"[A-Z]", value):
            raise ValueError("La contraseña debe incluir una mayúscula")
        if not re.search(r"[a-z]", value):
            raise ValueError("La contraseña debe incluir una minúscula")
        if not re.search(r"\d", value):
            raise ValueError("La contraseña debe incluir un número")
        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("La contraseña debe incluir un carácter especial")
        return value


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    # Exactamente 6 dígitos
    code: str = Field(pattern=r"^\d{6}$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Lo que se devuelve del usuario (sin contraseña ni datos del código)
class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_verified: bool
    created_at: datetime


class MessageResponse(BaseModel):
    message: str
