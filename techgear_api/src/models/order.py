from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class CartOrderItem(BaseModel):
    product_id: str = Field(min_length=24, max_length=24, pattern=r"^[a-fA-F0-9]{24}$")
    quantity: int = Field(gt=0, le=99)


class CartOrderModel(BaseModel):
    items: list[CartOrderItem] = Field(min_length=1, max_length=30)
    checkout_key: str | None = Field(default=None, min_length=16, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")


OrderStatus = Literal[
    "pendiente",
    "confirmado",
    "en_preparacion",
    "enviado",
    "entregado",
    "cancelado",
]


class OrderModel(BaseModel):
    product_id: str = Field(min_length=24, max_length=24, pattern=r"^[a-fA-F0-9]{24}$")
    quantity: int = Field(gt=0, le=99)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"product_id": "6701f2a8b4c9d1e2f3a4b5c6", "quantity": 2}
        }
    )


class OrderUpdateModel(BaseModel):
    status: OrderStatus

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "entregado",
            }
        }
    )
