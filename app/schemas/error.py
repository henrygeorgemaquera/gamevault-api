from typing import Any, Optional

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorBody
    detail: str
    request_id: Optional[str] = None
