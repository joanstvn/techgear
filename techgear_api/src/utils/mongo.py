from bson import ObjectId
from fastapi import HTTPException, status


def validate_object_id(id: str) -> ObjectId:
    """Valida si un string es un ObjectId válido de MongoDB."""
    if not ObjectId.is_valid(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El ID '{id}' no es un ObjectId válido de MongoDB",
        )
    return ObjectId(id)


def serialize_doc(doc: dict) -> dict:
    """Convierte el _id de MongoDB en un campo id de tipo string."""
    if not doc:
        return doc
    return {
        "id": str(doc["_id"]),
        **{k: v for k, v in doc.items() if k != "_id"},
    }
