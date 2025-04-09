# 用户模型
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


class ResponseTemplate(BaseModel):
    status: int
    message: str
    data: Optional[Any] = None


class UserInDB(BaseModel):
    username: str


class UserCreate(BaseModel):
    username: str
    password: str


class ProductInDB(BaseModel):
    name: str
    description: str
    price: float


class CouponCreate(BaseModel):
    code: str  # 优惠券代码
    discount_amount: float  # 优惠金额
    expiration_date: datetime  # 过期时间
