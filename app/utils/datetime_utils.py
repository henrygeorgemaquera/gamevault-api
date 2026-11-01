from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator


# Deja cualquier fecha de entrada en UTC con zona horaria (lo que SQLModel exige)
def to_utc(value: datetime) -> datetime:
    # Sin zona horaria: se asume que ya viene en UTC
    if value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    # Con zona horaria (ej: -03:00): se convierte a UTC
    return value.astimezone(timezone.utc)


# Tipo para los schemas y parámetros: Pydantic aplica to_utc al validar la entrada
UTCDatetime = Annotated[datetime, AfterValidator(to_utc)]
