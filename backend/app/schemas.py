from typing import Optional
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str

class CarOut(BaseModel):
    id: int
    brand: str
    model: str
    year: int
    price: int
    color: str
    url: str

class CarFilters(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    max_price: Optional[int] = None
    color: Optional[str] = None
