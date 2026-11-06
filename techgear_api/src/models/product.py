from typing import Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ProductModel(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=2000)
    price: float = Field(gt=0, allow_inf_nan=False)
    stock: int = Field(ge=0, le=1_000_000)
    category: str = Field(min_length=1, max_length=80)
    image: str = Field(
        ...,
        min_length=1,
        max_length=2000,
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
    name: Optional[str] = Field(None, min_length=1, max_length=160)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    price: Optional[float] = Field(None, gt=0, allow_inf_nan=False)
    stock: Optional[int] = Field(None, ge=0, le=1_000_000)
    category: Optional[str] = Field(None, min_length=1, max_length=80)
    image: Optional[str] = Field(
        None,
        min_length=1,
        max_length=2000,
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
