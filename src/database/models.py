from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index, Text
)
from sqlalchemy.orm import relationship
from src.database.session import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String(50), unique=True, index=True, nullable=False)
    product_name = Column(String(200), nullable=False)
    category = Column(String(100), index=True, nullable=False)
    unit_price = Column(Float, nullable=False, default=0.0)
    lead_time_days = Column(Float, nullable=False, default=7.0)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales = relationship("Sale", back_populates="product", cascade="all, delete-orphan")
    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="product", cascade="all, delete-orphan")
    recommendations = relationship("InventoryRecommendation", back_populates="product", cascade="all, delete-orphan")

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    sale_date = Column(DateTime, nullable=False, index=True)
    quantity_sold = Column(Float, nullable=False, default=0.0)
    unit_price = Column(Float, nullable=False, default=0.0)
    revenue = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="sales")

    __table_args__ = (
        Index("idx_sales_product_date", "product_id", "sale_date"),
    )

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False, index=True)
    quantity_available = Column(Float, nullable=False, default=0.0)
    quantity_reserved = Column(Float, nullable=False, default=0.0)
    quantity_on_order = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="inventory")

class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    forecast_date = Column(DateTime, nullable=False, index=True)
    predicted_demand = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=True)
    upper_bound = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="forecasts")

    __table_args__ = (
        Index("idx_forecast_product_date", "product_id", "forecast_date"),
    )

class InventoryRecommendation(Base):
    __tablename__ = "inventory_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    current_inventory = Column(Float, nullable=False)
    forecast_demand = Column(Float, nullable=False)
    lead_time_demand = Column(Float, nullable=False)
    safety_stock = Column(Float, nullable=False)
    reorder_point = Column(Float, nullable=False)
    recommended_quantity = Column(Float, nullable=False)
    stockout_risk = Column(String(20), nullable=False, index=True)
    recommendation = Column(String(50), nullable=False)
    explanation = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)

    product = relationship("Product", back_populates="recommendations")

class ModelRun(Base):
    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), unique=True, nullable=False, index=True)
    training_dates = Column(String(100), nullable=True)
    mae = Column(Float, nullable=False)
    rmse = Column(Float, nullable=False)
    mape = Column(Float, nullable=False)
    wape = Column(Float, nullable=True)
    status = Column(String(20), default="PRODUCTION", index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    artifact_path = Column(String(500), nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(200), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="VIEWER")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", backref="sessions")
