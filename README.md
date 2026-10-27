# GameVault UCN - Backend API

API REST desarrollada con FastAPI y SQLModel para la plataforma de distribución digital de videojuegos GameVault UCN.

## Tecnologías Utilizadas
- Python 3.12+
- FastAPI & Uvicorn
- SQLite & SQLModel (ORM)
- PyJWT & Passlib (Bcrypt)
- Resend (Correos transaccionales)
- Cloudinary (Gestión de imágenes)
- APScheduler (Tareas programadas)
- SlowAPI (Rate Limiting)

## Configuración e Instalación Local

1. **Crear y activar el entorno virtual:**
```bash
# En Windows (PowerShell):
python -m venv venv

.\venv\Scripts\Activate

# En Mac / Linux:
source venv/bin/activate
```
2. **Instalar las dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar los hooks de pre-commit:**
```bash
pre-commit install
```

4. **Configurar variables de entorno**
Crear un archivo .env en la raíz del proyecto basándose en la plantilla .env.example existente, y completar las credenciales correspondientes:
- DATABASE_URL: Ruta de conexión a SQLite (sqlite:///./gamevault.db).
- JWT_SECRET_KEY: Clave secreta para firmas los tokens JWT.
- JWT_ALGORITHM: Algoritmo de firma (HS256).
- ACCES_TOKEN_EXPIRE_MINUTES: Tiempo de expiración del token en minutos (60).
- RESEND_API_KEY: API Key del servicio Resend.
- CLOUDINARY_CLOUD_NAME: Credencial de Cloudinary (nombre de tu nube).
- CLOUDINARY_API_KEY: Credencial de Cloudinary (tu llave).
- CLOUDINARY_API_SECRET: Credencial de Cloudinary (tu clave secreta).

## Ejecución del servidor
Para iniciar el servidor en modo desarrollo
```bash
uvicorn app.main:app --reload
```
La documentación interactiva (Swagger UI) estará disponible en:
`http://127.0.0.1:8000/docs`
