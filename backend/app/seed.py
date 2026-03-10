import os
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.auth import hash_password

def seed_admin():
    email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("ADMIN_PASSWORD", "admin123")

    db: Session = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user:
            user.password_hash = hash_password(password)
        else:
            user = User(email=email, password_hash=hash_password(password), role="admin")
            db.add(user)
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
