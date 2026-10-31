import io
import logging
import uuid
from typing import Tuple

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps

from app.config.settings import settings

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def is_cloudinary_configured() -> bool:
    return bool(
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    )


def _configure_cloudinary() -> None:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_and_transform_game_image(
    file: UploadFile,
    game_id: int,
    width: int = 600,
    height: int = 800,
    crop: str = "fill",
) -> Tuple[str, str]:
    """
    Valida, transforma y almacena la imagen de un juego en Cloudinary.
    Retorna (image_url, image_public_id).
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagen no válido. Solo se permiten JPEG, PNG o WEBP",
        )

    raw_bytes = file.file.read()
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo de imagen está vacío",
        )
    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen supera el tamaño máximo permitido de 5 MB",
        )

    # Verifica que los bytes correspondan realmente a una imagen válida
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo subido no es una imagen válida",
        )

    if is_cloudinary_configured():
        _configure_cloudinary()
        public_id = f"gamevault/games/game_{game_id}_{uuid.uuid4().hex[:8]}"
        try:
            result = cloudinary.uploader.upload(
                raw_bytes,
                public_id=public_id,
                overwrite=True,
                resource_type="image",
                transformation=[
                    {
                        "width": width,
                        "height": height,
                        "crop": crop,
                        "quality": "auto",
                        "fetch_format": "auto",
                    }
                ],
            )
            return result["secure_url"], result["public_id"]
        except Exception:
            logger.exception(
                "Error al subir imagen a Cloudinary para game_id=%s", game_id
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No se pudo subir la imagen al servicio Cloudinary",
            )

    # Modo desarrollo local sin credenciales de Cloudinary: transforma con Pillow
    img_reopened = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    transformed = ImageOps.fit(img_reopened, (width, height))
    buffer = io.BytesIO()
    transformed.save(buffer, format="WEBP", quality=85)

    dev_public_id = f"dev_local/game_{game_id}_{uuid.uuid4().hex[:8]}"
    dev_url = (
        f"https://res.cloudinary.com/demo/image/upload/"
        f"c_{crop},w_{width},h_{height},q_auto,f_auto/{dev_public_id}.webp"
    )
    logger.info(
        "[MODO DEV] Imagen transformada localmente (%sx%s) para game_id=%s",
        width,
        height,
        game_id,
    )
    return dev_url, dev_public_id


def delete_game_image(public_id: str) -> None:
    """Elimina una imagen almacenada en Cloudinary mediante su public_id."""
    if not public_id:
        return

    if is_cloudinary_configured() and not public_id.startswith("dev_local/"):
        _configure_cloudinary()
        try:
            cloudinary.uploader.destroy(public_id, resource_type="image")
        except Exception:
            logger.exception(
                "Error al eliminar imagen en Cloudinary: public_id=%s", public_id
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No se pudo eliminar la imagen en Cloudinary",
            )
    else:
        logger.info("[MODO DEV] Imagen eliminada lógicamente: public_id=%s", public_id)
