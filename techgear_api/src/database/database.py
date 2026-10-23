import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Obtener la URI de conexión a la base de datos MongoDB desde las variables de entorno
MONGO_URI = os.getenv("MONGO_URL")

if not MONGO_URI:
    raise RuntimeError("La variable MONGO_URL no está definida. Revisa tu archivo .env")

# Instancia del cliente MongoDB con tiempo de espera de 3 segundos
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)

# Seleccionar la base de datos (utiliza la definida en la URI o 'techgear_db' por defecto)
try:
    db = client.get_default_database()
except Exception:
    db = client["techgear_db"]

# Colecciones principales para TechGear (Inventario y Pedidos)
products_collection = db.products
orders_collection = db.orders

try:
    # Verificar la conexión con el comando ping
    client.admin.command("ping")
    print("Conexión exitosa a MongoDB")
except (ConnectionFailure, ServerSelectionTimeoutError):
    print("Error al conectar a MongoDB. Revisa tus credenciales o el acceso por red.")