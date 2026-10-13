#!/usr/bin/env python3
"""Interactive first-admin provisioning. No hardcoded credentials."""
import getpass
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from src.database.session import SessionLocal, engine
from src.database.models import Base, User
from argon2 import PasswordHasher

ph = PasswordHasher()

def main():
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == "ADMIN").first()
        if existing:
            print("FAIL: Admin already exists (username:", existing.username, "). Refusing to create duplicate.")
            return
        username = input("Enter admin username (not 'admin' if you want custom): ").strip()
        if not username:
            print("FAIL: username required.")
            return
        password = getpass.getpass("Enter admin password: ")
        if len(password) < 8:
            print("FAIL: password must be >= 8 chars.")
            return
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("FAIL: passwords do not match.")
            return
        user = User(
            username=username,
            email="",
            password_hash=ph.hash(password),
            role="ADMIN",
            is_active=True
        )
        db.add(user)
        db.commit()
        print("OK: Admin created for username:", username, ". Remember this password — it is not stored elsewhere.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
