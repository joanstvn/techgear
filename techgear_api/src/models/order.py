from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class OrderModel(BaseModel):
    customer_name: str
    customer_email: EmailStr
    product: str
    quantity: int
    total_price: float
    status: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_name": "Carlos Rodríguez",
                "customer_email": "carlos.rodriguez@example.com",
                "product": "Teclado Mecánico RGB",
                "quantity": 2,
                "total_price": 159.98,
                "status": "pendiente",
            }
        }
    )


class OrderUpdateModel(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    product: Optional[str] = None
    quantity: Optional[int] = None
    total_price: Optional[float] = None
    status: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "completado",
            }
        }
    )
