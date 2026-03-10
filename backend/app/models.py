from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="admin")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    price = Column(Integer, nullable=False, index=True)
    color = Column(String, nullable=False, index=True)
    url = Column(String, nullable=False, unique=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
