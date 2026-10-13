import pytest
import os
os.environ["DATABASE_URL"] = "sqlite:///./test_auth.db"
from fastapi.testclient import TestClient
from src.api.main import app
from src.database.session import SessionLocal, get_db
from src.database.models import User, Session, Base
from src.config.settings import settings

# Dependency override for isolated test DB
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.session import Base

test_engine = create_engine("sqlite:///./test_auth.db", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

from src.api.main import app
app.dependency_overrides[get_db] = override_get_db
# Seed test admin for login tests
from src.database.session import SessionLocal as SeedDB
from src.database.models import User as SeedUser
from argon2 import PasswordHasher
seed_ph = PasswordHasher()
seed_db = SeedDB()
try:
    existing = seed_db.query(SeedUser).filter(SeedUser.username == "admin").first()
    if not existing:
        u = SeedUser(username="admin", password_hash=seed_ph.hash("AdminPass1!"), role="ADMIN", is_active=True)
        seed_db.add(u); seed_db.commit()
finally:
    seed_db.close()


from argon2 import PasswordHasher

client = TestClient(app)
ph = PasswordHasher()

def _setup_user(db, username="testuser", role="VIEWER", password="TestPass1!"):
    user = User(username=username, password_hash=ph.hash(password), role=role, is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    return user, password

def test_login_valid():
    db = SessionLocal()
    try:
        user, pw = _setup_user(db)
        res = client.post("/api/v1/auth/login", json={"username": user.username, "password": pw})
        assert res.status_code == 200
        data = res.json()
        assert data["username"] == user.username
        assert data["role"] == user.role
        assert len(data["token"]) > 20
    finally:
        db.close()

def test_login_invalid_username():
    res = client.post("/api/v1/auth/login", json={"username": "nonexistent", "password": "anything"})
    assert res.status_code == 401
    assert "Invalid" in res.json()["error"]["message"]

def test_login_wrong_password():
    db = SessionLocal()
    try:
        user, _ = _setup_user(db, username="badpass")
        res = client.post("/api/v1/auth/login", json={"username": user.username, "password": "wrong"})
        assert res.status_code == 401
    finally:
        db.close()

def test_auth_me_valid_token():
    db = SessionLocal()
    try:
        from secrets import token_urlsafe
        import hashlib
        user, pw = _setup_user(db, username="authtest")
        raw = token_urlsafe(32)
        h = hashlib.sha256(raw.encode()).hexdigest()
        s = Session(user_id=user.id, token_hash=h, expires_at=__import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(hours=8))
        db.add(s); db.commit()
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {raw}"})
        assert res.status_code == 200
        assert res.json()["username"] == "authtest"
    finally:
        db.close()

def test_auth_me_missing_token():
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401

def test_auth_me_revoked_token():
    db = SessionLocal()
    try:
        from secrets import token_urlsafe
        import hashlib
        from datetime import datetime
        user, pw = _setup_user(db, username="revoked")
        raw = token_urlsafe(32)
        h = hashlib.sha256(raw.encode()).hexdigest()
        s = Session(user_id=user.id, token_hash=h, expires_at=datetime.utcnow() + __import__("datetime").timedelta(hours=8), revoked_at=datetime.utcnow())
        db.add(s); db.commit()
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {raw}"})
        assert res.status_code == 401
    finally:
        db.close()

def test_train_anonymous_401():
    res = client.post("/api/v1/models/train")
    assert res.status_code == 401

def test_train_non_admin_403():
    db = SessionLocal()
    try:
        from secrets import token_urlsafe
        import hashlib
        from datetime import datetime, timedelta
        # Create viewer user
        from src.database.models import User, Session
        viewer = User(username="vieweronly", password_hash=ph.hash("TestPass1!"), role="VIEWER", is_active=True)
        db.add(viewer); db.commit(); db.refresh(viewer)
        raw = token_urlsafe(32)
        s = Session(user_id=viewer.id, token_hash=hashlib.sha256(raw.encode()).hexdigest(), expires_at=datetime.utcnow()+timedelta(hours=8))
        db.add(s); db.commit()
        res = client.post("/api/v1/models/train", headers={"Authorization": f"Bearer {raw}"})
        assert res.status_code == 403
    finally:
        db.close()

def test_products_create_401():
    res = client.post("/api/v1/products", json={"product_code":"T","product_name":"T","category":"C","unit_price":1,"lead_time_days":1,"active":True,"initial_inventory":0})
    assert res.status_code == 401

def test_forecast_create_403():
    db = SessionLocal()
    try:
        from secrets import token_urlsafe
        import hashlib
        from datetime import datetime, timedelta
        from src.database.models import User, Session
        viewer = User(username="forecastviewer", password_hash=ph.hash("TestPass1!"), role="VIEWER", is_active=True)
        db.add(viewer); db.commit(); db.refresh(viewer)
        raw = token_urlsafe(32)
        s = Session(user_id=viewer.id, token_hash=hashlib.sha256(raw.encode()).hexdigest(), expires_at=datetime.utcnow()+timedelta(hours=8))
        db.add(s); db.commit()
        res = client.post("/api/v1/forecasts", headers={"Authorization": f"Bearer {raw}"}, json={"product_id":"P001","horizon_days":7})
        assert res.status_code == 403
    finally:
        db.close()

def test_promote_401():
    res = client.post("/api/v1/models/v1.0.0/promote")
    assert res.status_code == 401
