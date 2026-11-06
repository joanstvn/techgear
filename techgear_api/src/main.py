import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from src.routes.auth import router as auth_router
from src.routes.orders import router as orders_router
from src.routes.products import router as products_router
from src.routes.users import router as users_router

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production" or bool(os.getenv("RENDER"))
API_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:8001,http://localhost:8001",
    ).split(",")
    if origin.strip()
]

app = FastAPI(
    title="TechGear API",
    description="API para la gestión del inventario de productos y registro de pedidos de TechGear.",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)


@app.exception_handler(PyMongoError)
async def handle_database_unavailable(_request: Request, _error: PyMongoError):
    """Return a safe, retryable response when MongoDB is unavailable."""
    return JSONResponse(
        status_code=503,
        content={"detail": "El servicio de datos no está disponible ahora. Inténtalo de nuevo."},
        headers={"Retry-After": "5"},
    )

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=API_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Rutas principales
app.include_router(auth_router, prefix="/auth", tags=["Autenticación"])
app.include_router(products_router, prefix="/products", tags=["Productos"])
app.include_router(orders_router, prefix="/orders", tags=["Pedidos"])
app.include_router(users_router, prefix="/users", tags=["Usuarios"])


@app.get("/", tags=["Inicio"])
def read_root():
    return {
        "message": "Bienvenido a la API de TechGear",
        "docs": "/docs",
        "redoc": "/redoc",
    }
