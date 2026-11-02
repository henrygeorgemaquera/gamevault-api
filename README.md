# GameVault UCN - Backend API

API REST para una plataforma de distribución digital de videojuegos. Permite explorar un catálogo público, armar un carrito, realizar compras **simuladas** con boleta en PDF, gestionar una lista de deseados y publicar reseñas. Incluye un backoffice para administradores. El frontend queda fuera del alcance: la API se prueba íntegramente con **Swagger UI**.

## Tecnologías

| Tecnología | Uso |
|---|---|
| Python 3.12 o superior | Lenguaje base |
| FastAPI + Uvicorn | API REST y servidor ASGI |
| SQLModel + SQLite | ORM relacional y base de datos |
| PyJWT + bcrypt | Sesiones con JWT y contraseñas hasheadas |
| Resend | Correos de verificación y confirmación de compra |
| Cloudinary + Pillow | Almacenamiento y transformación de imágenes del catálogo |
| APScheduler | Tareas programadas de mantenimiento |
| SlowAPI | Rate limiting por IP |
| ReportLab | Generación de boleta de compra en PDF |

Todas las dependencias están declaradas en `requirements.txt` con su versión exacta.

## Estructura del proyecto

El código está dividido en capas con responsabilidades separadas aplicando principios SOLID e inyección de dependencias:

```text
app/
├── config/          # settings (.env) y conexión a la base de datos
├── models/          # tablas relacionales (SQLModel)
├── schemas/         # contratos de entrada y salida de la API (Pydantic)
├── routers/         # endpoints (capa de transporte HTTP)
├── services/        # lógica y reglas de negocio
├── repositories/    # acceso a datos (interfaces abstractas + implementación ORM)
├── utils/           # seguridad, correos, PDF, jobs, logs, manejo de errores
└── main.py          # punto de entrada y configuración de la app
seed.py              # carga automática de datos semilla al iniciar
```

Cada router recibe su servicio y cada servicio recibe la abstracción de su repositorio mediante inyección de dependencias (`Depends`). Todas las consultas se realizan de forma parametrizada a través del ORM.

## Requisitos previos

- Python 3.12 o superior (probado en Python 3.12 y 3.14).
- Git.
- Opcional: una cuenta gratuita en [Resend](https://resend.com) (para enviar correos en registros nuevos) y en [Cloudinary](https://cloudinary.com) (para almacenar imágenes en la nube). El seeder automático ya crea usuarios verificados y juegos listos para probar sin requerir claves externas.

## Instalación

**1. Clonar el repositorio**
```bash
git clone https://github.com/henrygeorgemaquera/gamevault-api.git
cd gamevault-api
```

**2. Crear y activar el entorno virtual**
```powershell
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```
Si PowerShell bloquea la ejecución del script, ejecuta antes: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
```bash
# Windows (Git Bash)
python -m venv venv
source venv/Scripts/activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

**3. Instalar las dependencias**
```bash
pip install -r requirements.txt
```

**4. Crear el archivo `.env` a partir de la plantilla**
```powershell
# Windows (PowerShell)
Copy-Item .env.example .env
```
```bash
# Git Bash / Linux / macOS
cp .env.example .env
```

**5. Configurar tu clave secreta JWT**
`JWT_SECRET_KEY` es la única variable obligatoria para arrancar y **no viene incluida en el repositorio** por seguridad. Abre tu archivo `.env` y asigna una cadena secreta en `JWT_SECRET_KEY=` (por ejemplo: `JWT_SECRET_KEY=clave_secreta_desarrollo_gamevault_ucn_2026`), o genera una aleatoria ejecutando:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Configuración del `.env`

El archivo `.env.example` contiene la plantilla completa de variables sin credenciales reales.

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | No | Ruta de SQLite. Por defecto `sqlite:///./gamevault.db` |
| `JWT_SECRET_KEY` | **Sí** | Clave secreta para firmar tokens JWT y códigos HMAC |
| `JWT_ALGORITHM` | No | Algoritmo de firma. Por defecto `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Minutos de validez del token. Por defecto `60` |
| `RESEND_API_KEY` | Solo para registrar cuentas nuevas | API Key de Resend (`re_...`) |
| `EMAIL_FROM` | No | Remitente de correo. Por defecto `onboarding@resend.dev` |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | No | Credenciales de Cloudinary para subida de imágenes |
| `VERIFICATION_CODE_EXPIRE_MINUTES` | No | Vigencia del código de verificación en minutos (`10`) |
| `VERIFICATION_MAX_ATTEMPTS` | No | Intentos fallidos antes del bloqueo temporal (`5`) |
| `VERIFICATION_LOCK_MINUTES` | No | Duración del bloqueo en minutos (`15`) |
| `UNVERIFIED_ACCOUNT_TTL_HOURS` | No | Horas antes de purgar una cuenta no verificada (`24`) |
| `JOBS_INTERVAL_MINUTES` | No | Intervalo de ejecución de tareas programadas en minutos (`60`) |
| `RATE_LIMIT_REGISTER`, `RATE_LIMIT_VERIFY`, `RATE_LIMIT_LOGIN`, `RATE_LIMIT_LOGOUT` | No | Límites por IP en autenticación (`5/minute`, `10/minute`, `10/minute`, `30/minute`) |

**Sobre Resend:** sin dominio propio solo funciona el remitente `onboarding@resend.dev`, el cual entrega correos únicamente a la dirección asociada a tu cuenta de Resend.

**Sobre Cloudinary:** si no se configuran credenciales en `.env`, el endpoint del backoffice valida y transforma la imagen localmente en memoria con Pillow (JPEG, PNG o WEBP de hasta 5 MB) y devuelve una URL simulada. Con credenciales configuradas, la imagen se transforma y almacena directamente en Cloudinary.

## Ejecución

```bash
uvicorn app.main:app --reload
```

Al iniciar, la aplicación valida la configuración, crea automáticamente el archivo `gamevault.db`, genera el esquema de tablas y ejecuta el seeder de datos iniciales. **No se requiere ningún comando adicional.**

| URL | Descripción |
|---|---|
| http://127.0.0.1:8000/docs | **Swagger UI** (documentación interactiva y pruebas) |
| http://127.0.0.1:8000/redoc | Documentación alternativa (ReDoc) |
| http://127.0.0.1:8000/health | Estado operativo de la API, base de datos y servicios externos |

Para detener el servidor, presiona `Ctrl + C`.

### Base de datos y migraciones

El proyecto crea las tablas automáticamente en el arranque mediante `SQLModel.metadata.create_all`, creando únicamente las tablas que aún no existen.

- **Primera ejecución:** la base de datos `gamevault.db` se crea y puebla sola.
- **Reinicio limpio:** si deseas restablecer todos los datos a su estado original, detén el servidor, **elimina el archivo `gamevault.db`** y vuelve a ejecutar `uvicorn app.main:app --reload`.

### Datos iniciales (seeder)

El seeder (`seed.py`) se ejecuta en el evento `lifespan` al iniciar la aplicación e inserta registros únicamente si las tablas están vacías (es idempotente y no duplica datos al reiniciar).

| Usuario | Correo | Contraseña | Rol (`role`) |
|---|---|---|---|
| Administrador | `admin@gamevault.ucn.cl` | `Admin123!` | `admin` |
| Usuario de prueba 1 | `maria.torres@example.com` | `Password123!` | `user` |
| Usuario de prueba 2 | `carlos.rojas@example.com` | `Password123!` | `user` |

Las tres cuentas se crean verificadas (`is_verified=True`) y activas (`is_active=True`). Además, se cargan 5 clasificaciones (*Acción*, *RPG*, *Indie*, *Estrategia* y *Aventura*), 6 videojuegos (incluyendo ofertas vigentes, una oferta vencida y un título retirado con `is_active=False` para probar el borrado lógico), junto con pedidos y listas de deseados iniciales para probar de inmediato el reporte de popularidad.

## Uso de Swagger UI y autenticación

Abre http://127.0.0.1:8000/docs. Todos los endpoints están organizados por módulo e incluyen sus esquemas de validación y respuestas de error.

### Rutas públicas, protegidas y de administrador

| Nivel de acceso | Rutas | Requisito |
|---|---|---|
| Públicas | `/catalog/*`, `GET /games/{game_id}/reviews`, `/health`, `/auth/register`, `/auth/verify`, `/auth/login` | Ninguno |
| Invitado o usuario | `/cart/*` | Sesión activa o header `X-Cart-Token` para invitados |
| Protegidas (cliente) | `/orders/*`, `/wishlist/*`, `POST /games/{game_id}/reviews`, `/auth/me`, `/auth/logout` | Token JWT válido (`Bearer`) |
| Administrador | `/admin/*` | Token JWT de usuario con rol `admin` (responde `403 Forbidden` a rol `user`) |

### Cómo iniciar sesión en Swagger

1. Pulsa el botón **Authorize** (arriba a la derecha, junto al ícono del candado).
2. En **username** ingresa el correo (ej. `admin@gamevault.ucn.cl` o `maria.torres@example.com`) y en **password** su contraseña (`Admin123!` o `Password123!`).
3. Deja en blanco `client_id`, `client_secret` y `scope`.
4. Pulsa **Authorize** y luego **Close**. Swagger adjuntará automáticamente el header `Authorization: Bearer <token>` en tus peticiones.
5. Verifica tu sesión ejecutando `GET /auth/me`.

Para cerrar sesión, ejecuta `POST /auth/logout` (que revoca el identificador `jti` del token en la lista negra) y luego usa **Authorize -> Logout** en Swagger.

## Endpoints

| Módulo | Endpoints |
|---|---|
| Autenticación | `POST /auth/register`, `POST /auth/verify`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Catálogo público | `GET /catalog/games`, `GET /catalog/games/{game_id}`, `GET /catalog/classifications` |
| Carrito | `GET /cart`, `POST /cart/items`, `DELETE /cart/items/{game_id}` |
| Pedidos | `POST /orders/checkout`, `GET /orders`, `GET /orders/{order_id}` |
| Lista de deseados | `GET /wishlist`, `POST /wishlist`, `DELETE /wishlist/{game_id}` |
| Reseñas | `POST /games/{game_id}/reviews`, `GET /games/{game_id}/reviews` |
| Administración Backoffice | `GET/POST /admin/classifications`, `PUT/DELETE /admin/classifications/{id}`, `GET/POST /admin/games`, `PUT/DELETE /admin/games/{id}`, `POST/DELETE /admin/games/{id}/image`, `GET /admin/users`, `PATCH /admin/users/{id}/suspend`, `PATCH /admin/users/{id}/reactivate`, `GET /admin/reports/popularity` |
| Calidad y Entorno | `GET /health` |

## Reglas de negocio y calidad

- **Registro y contraseñas:** valida formato de correo único y fortaleza de contraseña (mínimo 8 caracteres, máximo 72 bytes, al menos una mayúscula, una minúscula, un número y un carácter especial).
- **Verificación de cuenta:** código de 6 dígitos hasheado con HMAC-SHA256 enviado por Resend (expira en 10 minutos). Al quinto intento fallido, la cuenta se bloquea por 15 minutos (`423 Locked`).
- **Sesiones y seguridad:** tokens JWT con `jti` revocable en lista negra al hacer logout, bloqueo inmediato (`403 Forbidden`) a cuentas suspendidas y límite de peticiones por IP con SlowAPI (`429 Too Many Requests`).
- **Tareas programadas:** limpieza automática cada hora de cuentas no verificadas con más de 24 horas de antigüedad y purga de tokens expirados en la lista negra.
- **Catálogo y borrado lógico:** las eliminaciones de juegos y clasificaciones aplican *soft delete* (`is_active=False`), ocultándolos del catálogo público sin perder la integridad histórica de compras previas. Las ofertas se activan y desactivan automáticamente según su ventana de vigencia (`offer_start_date` y `offer_end_date`).
- **Carrito y compra transaccional:** carrito de invitado mediante `X-Cart-Token` con fusión automática al iniciar sesión. El checkout valida precios y disponibilidad en tiempo real, ejecuta una transacción atómica (creación del pedido con precios congelados + vaciado de carrito con `rollback` ante fallos), garantiza idempotencia mediante el header `Idempotency-Key` y envía la boleta en PDF en segundo plano (`BackgroundTasks`).
- **Reseñas:** restringidas exclusivamente a usuarios que hayan comprado el título (`403 Forbidden` en caso contrario) y limitadas a una reseña por juego (`409 Conflict`).
- **Manejo centralizado de errores y Logging (Módulo 6):** todas las respuestas de error siguen un contrato JSON consistente (`{"error": {"code", "message", "details"}, "detail", "request_id"}`) sin exponer trazas internas. Todos los eventos críticos, accesos denegados y errores se registran de forma estructurada en consola y en `gamevault.log` con marca de tiempo UTC y `request_id`.

## Organización del equipo y flujo Git

El desarrollo se dividió en ramas `feature/` y `fix/` integradas hacia `develop` mediante Pull Requests con revisión cruzada obligatoria, commits bajo el estándar **Conventional Commits** y etiquetado de versiones (`git tag`).

| Módulo | Rama |
|---|---|
| 1. Identidad y seguridad | `feature/modulo-1-identidad-seguridad` |
| 2. Catálogo público y búsqueda | `feature/modulo-2-catalogo` |
| 3. Gestión administrativa (backoffice) | `feature/modulo-3-backoffice` |
| 4. Transaccionalidad y pedidos / 5. Comunidad | `feature/modulo-4-5-pedidos-comunidad` |
| 6. Aseguramiento de calidad y entorno | `feature/modulo-6-calidad-logging` |

Para activar las validaciones locales de código antes de cada commit (`pre-commit`):
```bash
pre-commit install
```
