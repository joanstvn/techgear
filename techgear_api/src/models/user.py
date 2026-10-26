from typing import Optional
from pydantic import BaseModel, EmailStr


class UserModel(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    role: str


class UserUpdateModel(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
