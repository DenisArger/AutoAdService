from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User, Car
from app.schemas import LoginRequest, TokenResponse
from app.auth import verify_password, create_access_token, get_current_user

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return {"access_token": token}

@app.get("/api/cars")
def list_cars(
    brand: str | None = Query(default=None),
    model: str | None = Query(default=None),
    year: int | None = Query(default=None),
    max_price: int | None = Query(default=None),
    color: str | None = Query(default=None),
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Car)
    if brand:
        stmt = stmt.where(Car.brand.ilike(f"%{brand}%"))
    if model:
        stmt = stmt.where(Car.model.ilike(f"%{model}%"))
    if color:
        stmt = stmt.where(Car.color.ilike(f"%{color}%"))
    if year:
        stmt = stmt.where(Car.year == year)
    if max_price is not None:
        stmt = stmt.where(Car.price <= max_price)
    stmt = stmt.order_by(Car.updated_at.desc())
    return db.execute(stmt).scalars().all()
