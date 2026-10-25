from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class APIErrorDetail(BaseModel):
    code: str
    message: str

class APIErrorResponse(BaseModel):
    error: APIErrorDetail

class ProductBase(BaseModel):
    product_code: str
    product_name: str
    category: str
    unit_price: float = Field(ge=0.0)
    lead_time_days: float = Field(ge=1.0)
    active: bool = True

class ProductCreate(ProductBase):
    initial_inventory: float = Field(default=100.0, ge=0.0)

class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = Field(default=None, ge=0.0)
    lead_time_days: Optional[float] = Field(default=None, ge=1.0)
    active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int
    current_inventory: float = 0.0
    on_order_quantity: float = 0.0
    created_at: str

class ForecastRequest(BaseModel):
    product_id: str
    horizon_days: int = Field(default=30, ge=7, le=90)

class ForecastItem(BaseModel):
    product_id: str
    forecast_date: str
    predicted_demand: float
    lower_bound: float
    upper_bound: float
    model_version: str
    generated_at: str

class ForecastResponse(BaseModel):
    product_id: str
    product_name: str
    category: str
    horizon_days: int
    model_version: str
    generated_at: str
    forecasts: List[ForecastItem]
    historical_sales: List[Dict[str, Any]]

class InventoryRecommendationItem(BaseModel):
    product_id: str
    product_name: str
    category: str
    current_inventory: float
    forecast_demand: float
    average_daily_demand: float
    lead_time_days: float
    lead_time_demand: float
    safety_stock: float
    reorder_point: float
    inventory_coverage_days: float
    recommended_order_quantity: int
    stockout_risk: str
    overstock_status: str
    recommendation: str
    explanation: Optional[str] = None

class InventoryAdjustmentRequest(BaseModel):
    quantity_delta: float = Field(ne=0, ge=-1000000, le=1000000)
    reason: str = Field(min_length=2, max_length=50)
    note: Optional[str] = Field(default=None, max_length=500)

class PurchaseOrderCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0, le=1000000)
    expected_arrival_date: Optional[datetime] = None
    note: Optional[str] = Field(default=None, max_length=500)

class DashboardSummaryResponse(BaseModel):
    kpis: Dict[str, Any]
    recommendations: List[InventoryRecommendationItem]
    risk_breakdown: Dict[str, int]
    category_summary: List[Dict[str, Any]]
    model_performance: Dict[str, Any]
    recent_forecast_runs: List[Dict[str, Any]]

class LoginRequest(BaseModel):
    username: str
    password: str

class RegistrationRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)

class UserProfile(BaseModel):
    id: str
    username: str
    name: str
    role: str
    token: str
    organization_id: int
    organization_name: str
