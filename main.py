from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
import jwt
from starlette.responses import RedirectResponse

from mock.db import Base, engine, SessionLocal
from mock.dependencies import get_db
from mock.models import Product, User, Cart, Order, Coupon
from mock.schemas import UserCreate, UserInDB, CouponCreate

# FastAPI 应用初始化
app = FastAPI()


@app.on_event("startup")
async def startup():
    # 创建数据库表
    Base.metadata.create_all(bind=engine)

    # 初始化一些示例产品
    db = SessionLocal()
    if db.query(Product).count() == 0:  # 仅在数据库为空时插入数据
        products = [
            Product(name="Product 1", description="Description for product 1", price=10.99),
            Product(name="Product 2", description="Description for product 2", price=20.99),
            Product(name="Product 3", description="Description for product 3", price=30.99),
            Product(name="Product 4", description="Description for product 4", price=40.99)
        ]
        db.add_all(products)
        db.commit()
    db.close()


# OAuth2 认证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# JWT 配置
SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Helper Functions
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Mock 数据
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


@app.post("/register", response_model=UserInDB)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user = User(username=user.username, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == form_data.username).first()
    if db_user is None or db_user.password != form_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/token/refresh")
async def refresh_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        new_token = create_access_token(data={"sub": username})
        return {"access_token": new_token, "token_type": "bearer"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/home")
async def home(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return {"products": products}


@app.get("/product/{product_id}")
async def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product": product}


@app.post("/cart/add")
async def add_to_cart(product_id: int, quantity: int, db: Session = Depends(get_db),
                      token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    cart_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity)
    db.add(cart_item)
    db.commit()
    return {"msg": "Product added to cart"}


@app.get("/cart")
async def get_cart(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    cart_items = db.query(Cart).filter(Cart.user_id == user_id).all()
    return {"cart": cart_items}


@app.post("/order")
async def create_order(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    cart_items = db.query(Cart).filter(Cart.user_id == user_id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total_price = sum(
        [item.quantity * db.query(Product).filter(Product.id == item.product_id).first().price for item in cart_items])
    order = Order(user_id=user_id, product_id=cart_items[0].product_id, quantity=cart_items[0].quantity,
                  total_price=total_price, status="pending")
    db.add(order)
    db.commit()
    return {"msg": "Order created", "order_id": order.id}


@app.get("/orders")
async def get_orders(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    orders = db.query(Order).filter(Order.user_id == user_id).all()
    return {"orders": orders}


@app.post("/pay/{order_id}")
async def pay(order_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme), amount: float = 0):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 检查是否有优惠券折扣
    if order.total_price < amount:
        raise HTTPException(status_code=400, detail="Payment amount exceeds the total order price")

    order.status = "paid"
    db.commit()
    return {"msg": "Payment successful", "order_id": order.id}


@app.delete("/cart/{cart_item_id}")
async def remove_from_cart(cart_item_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    cart_item = db.query(Cart).filter(Cart.id == cart_item_id, Cart.user_id == user_id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(cart_item)
    db.commit()
    return {"msg": "Product removed from cart"}


@app.put("/cart/{cart_item_id}")
async def update_cart_item(cart_item_id: int, quantity: int, db: Session = Depends(get_db),
                           token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    cart_item = db.query(Cart).filter(Cart.id == cart_item_id, Cart.user_id == user_id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

    cart_item.quantity = quantity
    db.commit()
    return {"msg": "Cart item updated"}


@app.delete("/order/{order_id}")
async def cancel_order(order_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id, Order.status == "pending").first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or cannot be cancelled")

    db.delete(order)
    db.commit()
    return {"msg": "Order cancelled"}


@app.get("/user_dashboard")
async def user_dashboard(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    cart_items = db.query(Cart).filter(Cart.user_id == user_id).all()
    orders = db.query(Order).filter(Order.user_id == user_id).all()

    return {"cart_items": cart_items, "orders": orders}


@app.get("/order/{order_id}/detail")
async def get_order_detail(order_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    product = db.query(Product).filter(Product.id == order.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"order_id": order.id, "product": product, "quantity": order.quantity, "total_price": order.total_price,
            "status": order.status}


@app.post("/admin/create_coupon")
async def create_coupon(coupon: CouponCreate, db: Session = Depends(get_db)):
    db_coupon = db.query(Coupon).filter(Coupon.code == coupon.code).first()
    if db_coupon:
        raise HTTPException(status_code=400, detail="Coupon code already exists")

    db_coupon = Coupon(
        code=coupon.code,
        discount_amount=coupon.discount_amount,
        expiration_date=coupon.expiration_date
    )
    db.add(db_coupon)
    db.commit()
    db.refresh(db_coupon)
    return {"msg": "Coupon created successfully", "coupon_id": db_coupon.id}


@app.get("/coupons")
async def get_valid_coupons(db: Session = Depends(get_db)):
    current_time = datetime.utcnow()
    valid_coupons = db.query(Coupon).filter(Coupon.active == True, Coupon.expiration_date > current_time).all()
    return {"coupons": valid_coupons}


@app.post("/order/apply_coupon")
async def apply_coupon(order_id: int, coupon_code: str, db: Session = Depends(get_db),
                       token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 查找订单
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 查找优惠券
    coupon = db.query(Coupon).filter(Coupon.code == coupon_code).first()
    if not coupon:
        raise HTTPException(status_code=400, detail="Invalid coupon code")

    # 检查优惠券是否过期
    if coupon.expiration_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Coupon has expired")

    # 更新订单总价
    discount = coupon.discount_amount
    if order.total_price < discount:
        discount = order.total_price  # 最大只能抵扣订单的总额

    order.total_price -= discount
    db.commit()

    return {"msg": "Coupon applied", "new_total_price": order.total_price}


@app.delete("/admin/delete_coupon/{coupon_id}")
async def delete_coupon(coupon_id: int, db: Session = Depends(get_db)):
    db_coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not db_coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    db.delete(db_coupon)
    db.commit()
    return {"msg": "Coupon deleted successfully"}


@app.delete("/user/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        # 解码 JWT token 来验证用户身份
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        current_user_id = db.query(User).filter(User.username == payload.get("sub")).first().id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 检查用户是否存在
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 防止删除自己
    if user_id == current_user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    # 删除用户
    db.delete(db_user)
    db.commit()
    return {"msg": "User deleted successfully"}
