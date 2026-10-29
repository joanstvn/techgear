# TechGear

Sistema de gestión de inventario y pedidos con un frontend en Django y una API en FastAPI + MongoDB.

## Estructura

```
techgear/
├── techgear_api/        # API REST (FastAPI + MongoDB)
│   └── src/
│       ├── models/      # Esquemas Pydantic
│       ├── routes/      # Endpoints (auth, products, orders, users)
│       ├── scripts/     # Utilidades (seed_admin)
│       └── utils/       # Seguridad JWT y helpers de MongoDB
└── techgear_web/        # Frontend (Django templates)
    └── store/
        ├── templates/   # Catálogo, login y paneles
        ├── static/      # CSS, JS e imágenes
        ├── api.py       # Cliente HTTP hacia FastAPI
        ├── forms.py
        ├── views.py
        └── tests.py
```

## Requisitos

- Python 3.12+
- MongoDB (local o Atlas)
- Dos entornos virtuales (o uno con ambos `requirements.txt`)

## Configuración

### 1. API

```bash
cd techgear_api
python -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edita MONGO_URL y JWT_SECRET
```

Crea el usuario administrador inicial:

```bash
python -m src.scripts.seed_admin
# Credenciales por defecto: admin / admin123
# También puedes usar --username, --email, --password y --full-name
```

Ejecuta la API:

```bash
uvicorn src.main:app --reload --port 8000
```

Documentación interactiva: <http://127.0.0.1:8000/docs>

### 2. Frontend

```bash
cd techgear_web
source ../venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8001
```

El frontend queda disponible en <http://127.0.0.1:8001>.

Si la API corre en otra URL, define la variable de entorno:

```bash
export TECHGEAR_API_URL="http://127.0.0.1:8000"
```

## Autenticación

- `POST /auth/login` valida las credenciales y devuelve un **JWT**.
- `GET /auth/me` devuelve el usuario autenticado a partir del token.
- Las rutas de `/users` requieren un token con rol `administrador`.
- Las contraseñas se almacenan con **PBKDF2-HMAC-SHA256** y nunca se devuelven en las respuestas.
- Django guarda el JWT en la sesión del servidor (`django.contrib.sessions`), por lo que el token no se expone al navegador; la cookie de sesión es `HttpOnly`.

Roles admitidos: `administrador` (acceso a los paneles) y `cliente`.

## Rutas del frontend

| Ruta | Descripción |
| --- | --- |
| `/` | Catálogo público con búsqueda y filtros por categoría |
| `/producto/<id>/` | Detalle del producto y formulario de pedido |
| `/login/` · `/logout/` | Inicio y cierre de sesión |
| `/panel/` | Panel de catálogo (productos) |
| `/panel/admin/` | Resumen general (solo administradores) |
| `/panel/admin/usuarios/` | Gestión de usuarios |
| `/panel/admin/pedidos/` | Pedidos y actualización de estados |

## Pruebas

```bash
cd techgear_web
python manage.py test store
```

## Notas

- Cambia `JWT_SECRET` y la contraseña del administrador antes de desplegar.
- `DEBUG`, `ALLOWED_HOSTS` y `SECRET_KEY` están configurados para desarrollo.
