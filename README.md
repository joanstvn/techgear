# TechGear

> Catálogo de robots humanoides con cuentas de cliente, carrito, seguimiento de pedidos y un panel de administración.

[Aplicación web](https://techgear-pi.vercel.app/) · [API en Render](https://techgear-api-gw90.onrender.com/)

TechGear está construido como dos servicios: una aplicación web Django que presenta la tienda y una API FastAPI que gestiona autenticación, productos, usuarios y pedidos. Los datos transaccionales viven en MongoDB Atlas.

## Contenido

- [Funciones](#funciones)
- [Tecnologías](#tecnologías)
- [Arquitectura](#arquitectura)
- [Flujo de compra y excepciones](#flujo-de-compra-y-excepciones)
- [Requisitos](#requisitos)
- [Instalación y ejecución local](#instalación-y-ejecución-local)
- [Variables de entorno](#variables-de-entorno)
- [Despliegue](#despliegue)
- [Rutas principales](#rutas-principales)
- [Seguridad](#seguridad)
- [Autor](#autor)

## Funciones

- Página de inicio, catálogo y detalle de cada producto.
- Registro e inicio de sesión para clientes; autenticación de administrador.
- Carrito que puede conservarse durante la sesión de navegación.
- Confirmación autenticada de pedidos y consulta de su estado en **Mis pedidos**.
- Cancelación de pedidos permitidos, con devolución de las unidades al inventario.
- Panel de administración para productos, usuarios y estados de pedidos.
- Imágenes de producto mediante archivos o URL; Cloudinary permite guardar de forma persistente las imágenes cargadas desde el panel.
- Diseño adaptable a móvil y escritorio.

## Tecnologías

| Área | Tecnologías |
| --- | --- |
| Web | Python, Django, plantillas HTML, CSS y JavaScript |
| API | Python, FastAPI, Pydantic, Uvicorn |
| Datos | MongoDB Atlas, PyMongo |
| Autenticación | JWT, PyJWT, contraseñas con hash |
| Cliente web → API | Requests |
| Archivos estáticos | WhiteNoise |
| Despliegue | Vercel (web) y Render (API) |
| Imágenes cargadas | Cloudinary (opcional) |

## Arquitectura

```text
techgear/
├── techgear_api/                 # API FastAPI
│   ├── src/
│   │   ├── routes/                # auth, products, orders, users
│   │   ├── models/                # esquemas y validaciones
│   │   ├── database/              # conexión y colecciones MongoDB
│   │   ├── utils/                 # JWT, permisos y utilidades Mongo
│   │   └── scripts/               # creación del administrador inicial
│   ├── .env.example
│   └── requirements.txt
└── techgear_web/                  # Aplicación Django
    ├── store/
    │   ├── templates/             # páginas y componentes HTML
    │   ├── static/store/          # CSS, JavaScript e imágenes
    │   ├── api.py                 # cliente HTTP para la API
    │   ├── views.py               # catálogo, carrito, pedidos y admin
    │   └── forms.py
    ├── settings.py
    ├── manage.py
    └── requirements.txt
```

## Flujo de compra y excepciones

1. El visitante explora el catálogo y agrega productos al carrito. Puede hacerlo antes de iniciar sesión; el carrito se conserva en la sesión web.
2. Al confirmar, si no hay una sesión autenticada, la web dirige al inicio de sesión y, después, devuelve al usuario al carrito.
3. Antes de enviar el pedido, Django vuelve a consultar productos y existencias. La API repite la validación y calcula los precios desde MongoDB; no confía en los totales enviados por el navegador.
4. La API descuenta el inventario y crea el pedido como **Pendiente** dentro de una transacción. Si no hay unidades suficientes, devuelve un conflicto y el usuario puede corregir el carrito.
5. Los reintentos de confirmación usan una clave de checkout para evitar pedidos duplicados.
6. El cliente consulta el seguimiento en **Mis pedidos**. Puede cancelar mientras el pedido siga pendiente. Administración puede avanzar los estados por la secuencia permitida; al cancelar antes del envío se restablece el inventario.
7. El pago y la coordinación de entrega se gestionan después de recibir el pedido; la aplicación no procesa pagos en línea.

Si MongoDB no responde, la API devuelve un error temporal `503` con `Retry-After`. Django convierte errores de conexión, tiempos de espera y respuestas de servidor en mensajes comprensibles, conserva la pantalla de la tienda y ofrece estados vacíos o una opción para reintentar según la sección. Si una operación de inventario falla, no se confirma el pedido parcialmente.

## Requisitos

- Python 3.12 o posterior.
- Una instancia de MongoDB Atlas o MongoDB compatible con transacciones (conjunto de réplicas).
- Git.
- Opcional: cuenta y credenciales de Cloudinary para persistir imágenes cargadas por el administrador.

## Instalación y ejecución local

### 1. Obtener el proyecto

```bash
git clone <URL_DEL_REPOSITORIO>
cd techgear
```

### 2. Preparar y ejecutar la API

En una terminal:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r techgear_api/requirements.txt
cp techgear_api/.env.example techgear_api/.env
```

Completa `techgear_api/.env` con una URI válida de MongoDB y secretos propios. Desde `techgear_api/`, inicia el servicio:

```bash
cd techgear_api
../.venv/bin/uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

La raíz de la API estará disponible en <http://127.0.0.1:8000/>. En desarrollo, la documentación interactiva está en <http://127.0.0.1:8000/docs>.

Para crear el administrador inicial, define `ADMIN_PASSWORD` en el entorno de la API (mínimo 12 caracteres) y ejecuta desde `techgear_api/`:

```bash
../.venv/bin/python -m src.scripts.seed_admin
```

### 3. Preparar y ejecutar la web

En otra terminal, activa el mismo entorno virtual:

```bash
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r techgear_web/requirements.txt
cd techgear_web
export DJANGO_DEBUG=1           # Windows PowerShell: $env:DJANGO_DEBUG="1"
export TECHGEAR_API_URL=http://127.0.0.1:8000
python manage.py migrate
python manage.py runserver 127.0.0.1:8001
```

Abre <http://127.0.0.1:8001/>. En desarrollo, Django usa una clave local de conveniencia si `DJANGO_SECRET_KEY` no está configurada; define una clave propia para cualquier entorno compartido.

## Variables de entorno

No publiques secretos en Git ni los incluyas en capturas o registros. El archivo `techgear_api/.env.example` contiene una plantilla para la API.

### API (Render y desarrollo)

| Variable | Uso |
| --- | --- |
| `MONGO_URL` | URI privada de MongoDB Atlas. |
| `JWT_SECRET` | Secreto aleatorio de al menos 32 caracteres para firmar tokens. |
| `JWT_ALGORITHM` | Algoritmo JWT; actualmente `HS256`. |
| `JWT_EXPIRE_MINUTES` | Vigencia del token de acceso. |
| `CORS_ORIGINS` | Orígenes web autorizados, separados por coma. En producción, usa `https://techgear-pi.vercel.app`. |
| `APP_ENV` | Usa `production` en Render para desactivar la documentación interactiva. |
| `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_FULL_NAME` | Datos del administrador creado con `seed_admin.py`. |

Genera secretos aleatorios localmente, por ejemplo con `python -c "import secrets; print(secrets.token_urlsafe(48))"`. No uses el valor de ejemplo en producción.

### Web (Vercel y desarrollo)

| Variable | Uso |
| --- | --- |
| `DJANGO_SECRET_KEY` | Clave de Django; obligatoria en producción y de al menos 50 caracteres aleatorios. |
| `DJANGO_DEBUG` | Usa `0` en producción y `1` solo para desarrollo local. |
| `DJANGO_ALLOWED_HOSTS` | Hosts adicionales, separados por coma. Añade `techgear-pi.vercel.app` si hace falta para el dominio asignado. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS confiables, separados por coma; por ejemplo `https://techgear-pi.vercel.app`. |
| `TECHGEAR_API_URL` | URL base de la API, sin barra final: `https://techgear-api-gw90.onrender.com`. |
| `TECHGEAR_API_TIMEOUT` | Tiempo límite general para peticiones de escritura (por defecto, 10 s). |
| `TECHGEAR_API_CONNECT_TIMEOUT`, `TECHGEAR_API_READ_TIMEOUT` | Límites de conexión y lectura para consultas GET. |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Credenciales opcionales para cargas persistentes de imágenes. |

## Despliegue

La web y la API se despliegan por separado; ambas deben apuntar a la misma base de MongoDB.

### Web en Vercel

- Repositorio: este proyecto.
- **Root Directory:** `techgear_web`.
- Framework: Django, detectado por Vercel.
- En **Settings → Environment Variables**, configura las variables de web de la tabla anterior para **Production**. En particular, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `TECHGEAR_API_URL` y el origen CSRF de producción.
- Haz un nuevo despliegue para aplicar cambios de variables.

URL pública: [https://techgear-pi.vercel.app/](https://techgear-pi.vercel.app/).

### API en Render

- **Root Directory:** `techgear_api`.
- Instala dependencias desde `requirements.txt`.
- Comando de inicio: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`.
- Configura las variables de API de la tabla anterior en **Environment**.
- `MONGO_URL` debe tener permisos sobre la base de datos y permitir conexiones desde Render.
- Mantén `CORS_ORIGINS` limitado a los dominios reales de la web.

URL pública: [https://techgear-api-gw90.onrender.com/](https://techgear-api-gw90.onrender.com/). El plan gratuito de Render puede suspender el servicio por inactividad; la primera petición después de una pausa puede tardar más.

## Rutas principales

### Sitio web

| Ruta | Descripción |
| --- | --- |
| `/` | Inicio. |
| `/catalogo/` | Catálogo público. |
| `/producto/<id>/` | Detalle del producto. |
| `/carrito/` | Revisión del carrito. |
| `/mis-pedidos/` | Historial del cliente autenticado. |
| `/login/`, `/registro/` | Acceso y creación de cuenta. |
| `/administracion/` | Panel de administración. |

### API

| Prefijo | Descripción |
| --- | --- |
| `/auth/` | Registro, inicio de sesión y usuario actual. |
| `/products/` | Consulta y administración de productos. |
| `/orders/` | Confirmación de carrito, pedidos propios y gestión administrativa. |
| `/users/` | Administración de usuarios. |

La API oculta Swagger y OpenAPI en producción; `/docs` solo está habilitado durante el desarrollo.

## Seguridad

- Las rutas administrativas de la API requieren un token JWT y rol de administrador.
- El registro público crea cuentas de cliente, no de administrador.
- El servidor valida precios, cantidades y stock antes de guardar un pedido.
- Las vistas web usan protección CSRF de Django; en producción se activan cookies seguras, redirección HTTPS y HSTS.
- Las sesiones usan cookies firmadas, `HttpOnly` y `SameSite=Lax`.
- Los secretos de Django, JWT, MongoDB y Cloudinary se configuran en el proveedor de despliegue, nunca en el código fuente.

## Autor

**Joan Stiven Ríos V** — proyecto TechGear.

