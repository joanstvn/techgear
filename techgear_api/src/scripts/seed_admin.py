import argparse
import os

from dotenv import load_dotenv

from src.database.database import users_collection
from src.utils.security import hash_password

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crea el usuario administrador inicial de TechGear.",
    )
    parser.add_argument("--username", default=os.getenv("ADMIN_USERNAME", "admin"))
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL", "admin@techgear.com"))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"))
    parser.add_argument(
        "--full-name",
        default=os.getenv("ADMIN_FULL_NAME", "Administrador TechGear"),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Actualiza la contraseña y el rol si el usuario ya existe.",
    )
    args = parser.parse_args()

    if not args.password or len(args.password) < 12:
        parser.error("Define ADMIN_PASSWORD o --password con al menos 12 caracteres.")

    email = args.email.lower()
    existing = users_collection.find_one(
        {"$or": [{"username": args.username}, {"email": email}]}
    )

    if existing and not args.force:
        print(
            f"El usuario '{args.username}' o el email '{email}' ya existen. "
            "Usa --force para actualizar sus credenciales."
        )
        return

    user_data = {
        "username": args.username,
        "email": email,
        "password": hash_password(args.password),
        "full_name": args.full_name,
        "role": "administrador",
    }

    if existing:
        users_collection.update_one({"_id": existing["_id"]}, {"$set": user_data})
        print(f"Usuario administrador '{args.username}' actualizado correctamente.")
    else:
        users_collection.insert_one(user_data)
        print(f"Usuario administrador '{args.username}' creado correctamente.")

    print(f"Email: {email}")


if __name__ == "__main__":
    main()
