# 用户模型
from pydantic import BaseModel


class UserInDB(BaseModel):
    username: str


class UserCreate(BaseModel):
    username: str
    password: str


class ProductInDB(BaseModel):
    name: str
    description: str
    price: float
