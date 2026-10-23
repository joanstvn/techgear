from typing import Optional
from pydantic import BaseModel, EmailStr


class OrderModel(BaseModel):
    customer_name: str
    customer_email: EmailStr
    product: str
    quantity: int
    total_price: float
    status: str


class OrderUpdateModel(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    product: Optional[str] = None
    quantity: Optional[int] = None
    total_price: Optional[float] = None
    status: Optional[str] = None
