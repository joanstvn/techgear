from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes.orders import router as orders_router
from src.routes.products import router as products_router

app = FastAPI(
    title="TechGear API",
    description="API para la gestión del inventario de productos y registro de pedidos de TechGear.",
    version="1.0.0",
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas principales
app.include_router(products_router, prefix="/products", tags=["Productos"])
app.include_router(orders_router, prefix="/orders", tags=["Pedidos"])


@app.get("/", tags=["Inicio"])
def read_root():
    return {
        "message": "Bienvenido a la API de TechGear",
        "docs": "/docs",
        "redoc": "/redoc",
    }
