from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean

from mock.db import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)


class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    price = Column(Float)


class Cart(Base):
    __tablename__ = 'carts'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    product_id = Column(Integer)
    quantity = Column(Integer)


class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    product_id = Column(Integer)
    quantity = Column(Integer)
    total_price = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(String, default=datetime.now().isoformat())


class Coupon(Base):
    __tablename__ = 'coupons'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # 优惠券代码
    discount_amount = Column(Float)  # 优惠金额或折扣比例
    expiration_date = Column(DateTime)  # 过期时间
    active = Column(Boolean, default=True)  # 是否有效



