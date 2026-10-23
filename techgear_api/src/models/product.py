from typing import Optional
from pydantic import BaseModel


class ProductModel(BaseModel):
    name: str
    description: str
    price: float
    stock: int
    category: str


class ProductUpdateModel(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    category: Optional[str] = None
