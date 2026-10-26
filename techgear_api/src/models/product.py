from typing import Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ProductModel(BaseModel):
    name: str
    description: str
    price: float
    stock: int
    category: str
    image: str = Field(
        ...,
        validation_alias=AliasChoices("image", "image_url"),
        description="URL o ruta de la imagen del producto",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "name": "Teclado Mecánico RGB",
                "description": "Teclado mecánico switches táctiles y retroiluminación RGB",
                "price": 79.99,
                "stock": 25,
                "category": "Periféricos",
                "image": "https://ejemplo.com/imagenes/teclado.jpg",
            }
        },
    )


class ProductUpdateModel(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    category: Optional[str] = None
    image: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("image", "image_url"),
        description="URL o ruta de la imagen del producto",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "price": 69.99,
                "stock": 30,
                "image": "https://ejemplo.com/imagenes/teclado-actualizado.jpg",
            }
        },
    )
