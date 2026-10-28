import os
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status, Header, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_

from src.config.settings import settings
from src.database.session import get_db, SessionLocal
from src.database.models import (
    Product, Sale, Inventory, Forecast, InventoryRecommendation, ModelRun, User, Session,
    InventoryTransaction, PurchaseOrder, TrainingJob, Organization, OrganizationMembership
)
from src.data.ingestion import load_and_prepare_data
from src.data.validation import validate_dataset
from src.data.cleaning import clean_sales_data
from src.forecasting.engine import ForecastEngine
from src.optimization.inventory import InventoryOptimizer
from src.models.trainer import ModelTrainingPipeline
from src.api.schemas import (
    ProductResponse, ProductCreate, ProductUpdate,
    ForecastRequest, ForecastResponse, ForecastItem,
    InventoryRecommendationItem, DashboardSummaryResponse, InventoryAdjustmentRequest, PurchaseOrderCreate,
    LoginRequest, UserProfile, RegistrationRequest
)
from src.utils.logger import logger


from argon2 import PasswordHasher
from secrets import token_urlsafe
import hashlib
ph = PasswordHasher()

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def _require_auth(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    if not authorization:
        create_error('UNAUTHORIZED', 'Authentication required.', 401)
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        create_error('UNAUTHORIZED', 'Invalid authorization format.', 401)
    raw_token = parts[1]
    token_hash = _hash_token(raw_token)
    session = db.query(Session).filter(Session.token_hash == token_hash).first()
    if not session or session.revoked_at is not None or session.expires_at < datetime.utcnow():
        create_error('UNAUTHORIZED', 'Session invalid, expired, or revoked.', 401)
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        create_error('UNAUTHORIZED', 'User account disabled.', 401)
    membership = db.query(OrganizationMembership).filter(OrganizationMembership.user_id == user.id).order_by(OrganizationMembership.id).first()
    if not membership:
        create_error('WORKSPACE_REQUIRED', 'This account is not assigned to a workspace.', 403)
    # Attach the selected workspace to this request-scoped user object. API
    # handlers must derive every business-data query from this value.
    user.organization_id = membership.organization_id
    user.role = membership.role
    return user


def _organization_id(user: User) -> int:
    organization_id = getattr(user, "organization_id", None)
    if not organization_id:
        create_error("WORKSPACE_REQUIRED", "No active workspace is available for this account.", 403)
    return int(organization_id)


def _workspace_data_path(organization_id: int) -> Path:
    return settings.base_dir / "data" / "workspaces" / str(organization_id) / "historical_sales.csv"


def _workspace_read_data_path(organization_id: int) -> Path:
    """Return the workspace dataset, with a one-time compatibility fallback.

    Existing installations had their first dataset at data/raw/historical_sales.csv
    before workspace folders existed. Only the migrated default workspace may read
    that legacy file; newly registered organisations never use it.
    """
    workspace_path = _workspace_data_path(organization_id)
    if workspace_path.exists():
        return workspace_path
    legacy_path = settings.base_dir / "data" / "raw" / "historical_sales.csv"
    if organization_id == 1 and legacy_path.exists():
        return legacy_path
    return workspace_path


def _workspace_model_dir(organization_id: int) -> Path:
    return settings.base_dir / "models" / "workspaces" / str(organization_id)


def _workspace_forecast_engine(organization_id: int) -> ForecastEngine:
    model_dir = _workspace_model_dir(organization_id)
    workspace_model = model_dir / "demand_model.joblib"
    workspace_metadata = model_dir / "metadata.json"
    if workspace_model.exists():
        return ForecastEngine(workspace_model, workspace_metadata)

    # The first installation predates organization-scoped model folders. Its
    # already-trained production model remains valid for the migrated default
    # workspace only. New organizations must train their own model.
    if organization_id == 1 and Path(settings.model_path).exists():
        return ForecastEngine(settings.model_path, settings.metadata_path)
    return ForecastEngine(workspace_model, workspace_metadata)


def _session_from_authorization(authorization: Optional[str], db: Session) -> Session:
    """Resolve an active session from a Bearer header for session lifecycle actions."""
    if not authorization:
        create_error('UNAUTHORIZED', 'Authentication required.', 401)
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        create_error('UNAUTHORIZED', 'Invalid authorization format.', 401)
    session = db.query(Session).filter(Session.token_hash == _hash_token(parts[1])).first()
    if not session or session.revoked_at is not None or session.expires_at < datetime.utcnow():
        create_error('UNAUTHORIZED', 'Session invalid, expired, or revoked.', 401)
    return session

router = APIRouter(prefix="/api/v1")

# Cache cleaned dataset keyed by file mtime to avoid re-parsing the CSV on every request.
_cleaned_cache: Dict[str, Any] = {}
_pending_uploads: Dict[str, Path] = {}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _get_cleaned_data(organization_id: int):
    """Return cached cleaned DataFrame, re-loading only if the source CSV changed."""
    raw_path = _workspace_read_data_path(organization_id)
    try:
        mtime = raw_path.stat().st_mtime
    except OSError:
        mtime = None
    cache_key = str(raw_path)
    cached = _cleaned_cache.get(cache_key)
    if not cached or cached["mtime"] != mtime:
        clean_df, _, _ = load_and_prepare_data(raw_path)
        _cleaned_cache[cache_key] = {"df": clean_df, "mtime": mtime}
    return _cleaned_cache[cache_key]["df"]


def invalidate_cleaned_cache():
    """Drop the cached cleaned dataset (call after retraining/re-ingestion)."""
    _cleaned_cache.clear()


def _require_data_import_role(user: User) -> None:
    if user.role not in {"ADMIN", "DATA_SCIENTIST"}:
        create_error("FORBIDDEN", "Your role cannot import sales data.", 403)


def _replace_workspace_data(db: Session, clean_df, organization_id: int) -> Dict[str, int]:
    """Replace operational records so every screen uses the newly imported dataset."""
    import pandas as pd

    # An import replaces a workspace, so its dependent operational records must
    # change together. Accounts and model-run history remain intact.
    workspace_products = db.query(Product).filter(Product.organization_id == organization_id).all()
    workspace_product_ids = [product.id for product in workspace_products]
    if workspace_product_ids:
        db.query(PurchaseOrder).filter(PurchaseOrder.product_id.in_(workspace_product_ids)).delete(synchronize_session=False)
        db.query(InventoryTransaction).filter(InventoryTransaction.product_id.in_(workspace_product_ids)).delete(synchronize_session=False)
        db.query(InventoryRecommendation).filter(InventoryRecommendation.product_id.in_(workspace_product_ids)).delete(synchronize_session=False)
        db.query(Forecast).filter(Forecast.product_id.in_(workspace_product_ids)).delete(synchronize_session=False)
        db.query(Sale).filter(Sale.product_id.in_(workspace_product_ids)).delete(synchronize_session=False)
        db.query(Inventory).filter(Inventory.product_id.in_(workspace_product_ids)).delete(synchronize_session=False)
        db.query(Product).filter(Product.id.in_(workspace_product_ids)).delete(synchronize_session=False)
    db.flush()

    products_by_code: Dict[str, Product] = {}
    for product_code, group in clean_df.groupby("product_id", sort=True):
        latest = group.sort_values("date").iloc[-1]
        product = Product(
            organization_id=organization_id,
            product_code=str(product_code),
            product_name=str(latest["product_name"]),
            category=str(latest["category"]),
            unit_price=float(latest["unit_price"]),
            lead_time_days=float(latest["lead_time_days"]),
            active=True,
        )
        db.add(product)
        db.flush()
        products_by_code[str(product_code)] = product
        db.add(Inventory(
            product_id=product.id,
            quantity_available=float(latest["inventory_level"]),
            quantity_reserved=0.0,
            quantity_on_order=0.0,
        ))

    sales = [
        Sale(
            product_id=products_by_code[str(row.product_id)].id,
            sale_date=pd.to_datetime(row.date).to_pydatetime(),
            quantity_sold=float(row.quantity_sold),
            unit_price=float(row.unit_price),
            revenue=float(row.revenue),
        )
        for row in clean_df.itertuples(index=False)
    ]
    db.bulk_save_objects(sales)
    db.commit()
    return {"products": len(products_by_code), "sales_records": len(sales)}


def _refresh_forecasts_and_recommendations(db: Session, organization_id: int) -> None:
    """Create saved dashboard outputs after a successful training run."""
    clean_df = _get_cleaned_data(organization_id)
    engine = _workspace_forecast_engine(organization_id)
    optimizer = InventoryOptimizer(service_level=settings.default_service_level)

    products = db.query(Product).filter(Product.organization_id == organization_id, Product.active.is_(True)).all()
    product_ids = [product.id for product in products]
    if product_ids:
        db.query(Forecast).filter(Forecast.product_id.in_(product_ids)).delete(synchronize_session=False)
        db.query(InventoryRecommendation).filter(InventoryRecommendation.product_id.in_(product_ids)).delete(synchronize_session=False)
    db.flush()

    for product in products:
        forecasts = engine.generate_forecast(clean_df, product.product_code, horizon_days=30)
        for item in forecasts:
            db.add(Forecast(
                product_id=product.id,
                forecast_date=datetime.strptime(item["forecast_date"], "%Y-%m-%d"),
                predicted_demand=float(item["predicted_demand"]),
                lower_bound=float(item["lower_bound"]),
                upper_bound=float(item["upper_bound"]),
                model_version=str(item["model_version"]),
            ))

        inventory = db.query(Inventory).filter(Inventory.product_id == product.id).first()
        history = clean_df[clean_df["product_id"].astype(str) == product.product_code]["quantity_sold"]
        decision = optimizer.optimize_product(
            product_id=product.product_code,
            product_name=product.product_name,
            current_inventory=inventory.quantity_available if inventory else 0.0,
            on_order_quantity=inventory.quantity_on_order if inventory else 0.0,
            forecast_daily_demands=[float(item["predicted_demand"]) for item in forecasts],
            lead_time_days=product.lead_time_days,
            historical_std_dev=float(history.std()) if len(history) > 1 else 0.0,
            planning_horizon_days=30,
        )
        db.add(InventoryRecommendation(
            product_id=product.id,
            current_inventory=decision["current_inventory"],
            forecast_demand=decision["forecast_demand"],
            lead_time_demand=decision["lead_time_demand"],
            safety_stock=decision["safety_stock"],
            reorder_point=decision["reorder_point"],
            recommended_quantity=decision["recommended_order_quantity"],
            stockout_risk=decision["stockout_risk"],
            recommendation=decision["recommendation"],
            explanation=decision["explanation"],
        ))
    db.commit()


def _normalise_upload_columns(raw_df, default_inventory: float, default_lead_time: float):
    """Map common transaction-export headers into DemandIQ's canonical schema."""
    aliases = {
        "date": {"date", "sale_date", "sales_date", "transaction_date"},
        "product_id": {"product_id", "productid", "sku", "sku_id", "item_id"},
        "product_name": {"product_name", "product", "item_name", "product_description"},
        "category": {"category", "product_category", "productcategory"},
        "quantity_sold": {"quantity_sold", "quantity", "units_sold", "units", "sales_quantity"},
        "unit_price": {"unit_price", "price", "selling_price", "sales_price"},
        "revenue": {"revenue", "sales_amount", "sales", "amount", "total_sales"},
        "inventory_level": {"inventory_level", "inventory", "stock_level", "on_hand"},
        "lead_time_days": {"lead_time_days", "lead_time", "lead_days", "supplier_lead_time"},
    }
    normalized = {str(column).strip().lower().replace(" ", "_"): column for column in raw_df.columns}
    rename_map, applied = {}, {}
    for canonical, options in aliases.items():
        if canonical in raw_df.columns:
            continue
        source = next((normalized[option] for option in options if option in normalized), None)
        if source:
            rename_map[source] = canonical
            applied[canonical] = source
    df = raw_df.rename(columns=rename_map).copy()

    generated = []
    if "product_name" not in df.columns and "product_id" in df.columns:
        df["product_name"] = "Product " + df["product_id"].astype(str)
        generated.append("product_name")
    if "inventory_level" not in df.columns:
        df["inventory_level"] = default_inventory
        generated.append("inventory_level")
    else:
        df["inventory_level"] = df["inventory_level"].fillna(default_inventory)
    if "lead_time_days" not in df.columns:
        df["lead_time_days"] = default_lead_time
        generated.append("lead_time_days")
    else:
        df["lead_time_days"] = df["lead_time_days"].fillna(default_lead_time)
    if "revenue" not in df.columns and {"quantity_sold", "unit_price"}.issubset(df.columns):
        df["revenue"] = df["quantity_sold"] * df["unit_price"]
        generated.append("revenue")
    return df, applied, generated

# Helper error response
def create_error(code: str, message: str, status_code: int = 400):
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})

# ----------------- System & Health -----------------

@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "service": "DemandIQ AI REST Engine",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/system/status")
def get_system_status(current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    organization_id = _organization_id(current_user)
    try:
        db_check = db.query(Product).filter(Product.organization_id == organization_id).count()
        db_status = "OPERATIONAL"
    except Exception as e:
        db_status = f"ERROR: {str(e)}"

    metadata: Dict[str, Any] = {}
    forecast_engine = _workspace_forecast_engine(organization_id)
    try:
        metadata = forecast_engine.get_metadata()
        model_status = "LOADED" if metadata.get("status") == "PRODUCTION" else "STANDBY"
    except Exception:
        model_status = "UNAVAILABLE"

    last_model_run = db.query(ModelRun).filter(ModelRun.organization_id == organization_id).order_by(ModelRun.timestamp.desc()).first()
    last_forecast = db.query(Forecast).join(Product).filter(Product.organization_id == organization_id).order_by(Forecast.generated_at.desc()).first()
    latest_sale = db.query(Sale).join(Product).filter(Product.organization_id == organization_id).order_by(Sale.sale_date.desc()).first()

    return {
        "api_status": "ONLINE",
        "database_status": db_status,
        "model_status": model_status,
        "production_model": metadata.get("model_name", "Random Forest"),
        "production_version": metadata.get("model_version", "v1.0.0"),
        "last_training_run": last_model_run.timestamp.isoformat() if last_model_run else None,
        "last_forecast_generation": last_forecast.generated_at.isoformat() if last_forecast else None,
        "data_freshness_date": latest_sale.sale_date.strftime("%Y-%m-%d") if latest_sale else None,
        "system_version": "1.0.0",
        "environment": settings.app_env,
    }

# ----------------- Products -----------------

@router.get("/products", response_model=List[ProductResponse])
def get_products(category: Optional[str] = None, current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    query = db.query(Product).filter(Product.organization_id == _organization_id(current_user))
    if category:
        query = query.filter(Product.category == category)
    products = query.order_by(Product.product_code).all()

    res = []
    for p in products:
        inv = db.query(Inventory).filter(Inventory.product_id == p.id).first()
        res.append(ProductResponse(
            id=p.id,
            product_code=p.product_code,
            product_name=p.product_name,
            category=p.category,
            unit_price=p.unit_price,
            lead_time_days=p.lead_time_days,
            active=p.active,
            current_inventory=inv.quantity_available if inv else 0.0,
            on_order_quantity=inv.quantity_on_order if inv else 0.0,
            created_at=p.created_at.isoformat() if p.created_at else datetime.utcnow().isoformat()
        ))
    return res

def _get_product(db: Session, product_id: str, organization_id: int):
    """Resolve a product by product_code or numeric id safely."""
    query = db.query(Product).filter(Product.organization_id == organization_id)
    if product_id.isdigit():
        query = query.filter(or_(Product.product_code == product_id, Product.id == int(product_id)))
    else:
        query = query.filter(Product.product_code == product_id)
    return query.first()


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product_detail(product_id: str, current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    prod = _get_product(db, product_id, _organization_id(current_user))
    if not prod:
        create_error("PRODUCT_NOT_FOUND", f"The requested product '{product_id}' does not exist.", 404)

    inv = db.query(Inventory).filter(Inventory.product_id == prod.id).first()
    return ProductResponse(
        id=prod.id,
        product_code=prod.product_code,
        product_name=prod.product_name,
        category=prod.category,
        unit_price=prod.unit_price,
        lead_time_days=prod.lead_time_days,
        active=prod.active,
        current_inventory=inv.quantity_available if inv else 0.0,
        on_order_quantity=inv.quantity_on_order if inv else 0.0,
        created_at=prod.created_at.isoformat() if prod.created_at else datetime.utcnow().isoformat()
    )

@router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(payload: ProductCreate, current_user = Depends(_require_auth), db: Session = Depends(get_db)):
    if current_user.role not in ROLE_PERMISSIONS or "edit_products" not in ROLE_PERMISSIONS.get(current_user.role, []):
        create_error("FORBIDDEN", "Insufficient permissions.", 403)
    organization_id = _organization_id(current_user)
    existing = db.query(Product).filter(Product.product_code == payload.product_code, Product.organization_id == organization_id).first()
    if existing:
        create_error("INVALID_REQUEST", f"Product code '{payload.product_code}' already exists.", 400)

    prod = Product(
        organization_id=organization_id,
        product_code=payload.product_code,
        product_name=payload.product_name,
        category=payload.category,
        unit_price=payload.unit_price,
        lead_time_days=payload.lead_time_days,
        active=payload.active
    )
    db.add(prod)
    db.flush()

    inv = Inventory(
        product_id=prod.id,
        quantity_available=payload.initial_inventory,
        quantity_reserved=0.0,
        quantity_on_order=0.0
    )
    db.add(inv)
    db.commit()

    return ProductResponse(
        id=prod.id,
        product_code=prod.product_code,
        product_name=prod.product_name,
        category=prod.category,
        unit_price=prod.unit_price,
        lead_time_days=prod.lead_time_days,
        active=prod.active,
        current_inventory=inv.quantity_available,
        on_order_quantity=inv.quantity_on_order,
        created_at=prod.created_at.isoformat()
    )

@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: str, payload: ProductUpdate, current_user = Depends(_require_auth), db: Session = Depends(get_db)):
    if current_user.role not in ROLE_PERMISSIONS or "edit_products" not in ROLE_PERMISSIONS.get(current_user.role, []):
        create_error("FORBIDDEN", "Insufficient permissions.", 403)
    prod = _get_product(db, product_id, _organization_id(current_user))
    if not prod:
        create_error("PRODUCT_NOT_FOUND", f"The requested product '{product_id}' does not exist.", 404)

    if payload.product_name is not None:
        prod.product_name = payload.product_name
    if payload.category is not None:
        prod.category = payload.category
    if payload.unit_price is not None:
        prod.unit_price = payload.unit_price
    if payload.lead_time_days is not None:
        prod.lead_time_days = payload.lead_time_days
    if payload.active is not None:
        prod.active = payload.active

    db.commit()
    inv = db.query(Inventory).filter(Inventory.product_id == prod.id).first()
    return ProductResponse(
        id=prod.id,
        product_code=prod.product_code,
        product_name=prod.product_name,
        category=prod.category,
        unit_price=prod.unit_price,
        lead_time_days=prod.lead_time_days,
        active=prod.active,
        current_inventory=inv.quantity_available if inv else 0.0,
        on_order_quantity=inv.quantity_on_order if inv else 0.0,
        created_at=prod.created_at.isoformat()
    )

# ----------------- Forecasts -----------------

@router.post("/forecasts", response_model=ForecastResponse)
def generate_forecast_endpoint(payload: ForecastRequest, current_user = Depends(_require_auth), db: Session = Depends(get_db)):
    if current_user.role not in ROLE_PERMISSIONS or "create_forecasts" not in ROLE_PERMISSIONS.get(current_user.role, []):
        create_error("FORBIDDEN", "Insufficient permissions.", 403)
    organization_id = _organization_id(current_user)
    prod = _get_product(db, payload.product_id, organization_id)
    if not prod:
        create_error("PRODUCT_NOT_FOUND", f"Product '{payload.product_id}' not found.", 404)

    raw_data_path = _workspace_read_data_path(organization_id)
    if not raw_data_path.exists():
        create_error("INTERNAL_SERVER_ERROR", "Historical dataset not initialized.", 500)

    clean_df = _get_cleaned_data(organization_id)
    engine = _workspace_forecast_engine(organization_id)

    try:
        forecast_items = engine.generate_forecast(
            historical_df=clean_df,
            product_id=prod.product_code,
            horizon_days=payload.horizon_days
        )
    except FileNotFoundError:
        create_error("MODEL_UNAVAILABLE", "Forecasting model is currently unavailable or training.", 503)
    except Exception as e:
        create_error("INTERNAL_SERVER_ERROR", f"Forecasting calculation error: {str(e)}", 500)

    # Fetch last 30 days historical sales for comparative graph
    recent_sales = db.query(Sale).filter(Sale.product_id == prod.id).order_by(Sale.sale_date.desc()).limit(30).all()
    recent_sales_data = [
        {"date": s.sale_date.strftime("%Y-%m-%d"), "actual_demand": s.quantity_sold, "revenue": s.revenue}
        for s in reversed(recent_sales)
    ]

    metadata = engine.get_metadata()
    return ForecastResponse(
        product_id=prod.product_code,
        product_name=prod.product_name,
        category=prod.category,
        horizon_days=payload.horizon_days,
        model_version=metadata.get("model_version", "v1.0.0"),
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        forecasts=[ForecastItem(**f) for f in forecast_items],
        historical_sales=recent_sales_data
    )

@router.get("/forecasts/history")
def get_forecast_history(product_id: Optional[str] = None, current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    query = db.query(Forecast).join(Product).filter(Product.organization_id == _organization_id(current_user))
    if product_id:
        query = query.filter(Product.product_code == product_id)
    records = query.order_by(Forecast.forecast_date.asc()).limit(200).all()

    return [
        {
            "id": r.id,
            "product_code": r.product.product_code,
            "product_name": r.product.product_name,
            "category": r.product.category,
            "forecast_date": r.forecast_date.strftime("%Y-%m-%d"),
            "predicted_demand": r.predicted_demand,
            "lower_bound": r.lower_bound,
            "upper_bound": r.upper_bound,
            "model_version": r.model_version,
            "generated_at": r.generated_at.isoformat()
        }
        for r in records
    ]

# ----------------- Inventory & Recommendations -----------------

@router.get("/inventory/recommendations", response_model=List[InventoryRecommendationItem])
def get_recommendations(
    risk: Optional[str] = None,
    category: Optional[str] = None,
    current_user=Depends(_require_auth),
    db: Session = Depends(get_db)
):
    query = db.query(InventoryRecommendation).join(Product).filter(Product.organization_id == _organization_id(current_user))
    if risk:
        query = query.filter(InventoryRecommendation.stockout_risk == risk.upper())
    if category:
        query = query.filter(Product.category == category)

    recs = query.order_by(
        # Critical and High risks first
        case(
            (InventoryRecommendation.stockout_risk == "CRITICAL", 1),
            (InventoryRecommendation.stockout_risk == "HIGH", 2),
            (InventoryRecommendation.stockout_risk == "MEDIUM", 3),
            else_=4
        )
    ).all()

    items = []
    for r in recs:
        p = r.product
        avg_daily = round(r.forecast_demand / 30.0, 2) if r.forecast_demand > 0 else 0.0
        coverage = round(r.current_inventory / avg_daily, 1) if avg_daily > 0 else 999.0
        is_overstocked = r.recommendation == "OVERSTOCK" or coverage > max(60.0, p.lead_time_days * 4)

        items.append(InventoryRecommendationItem(
            product_id=p.product_code,
            product_name=p.product_name,
            category=p.category,
            current_inventory=r.current_inventory,
            forecast_demand=r.forecast_demand,
            average_daily_demand=avg_daily,
            lead_time_days=p.lead_time_days,
            lead_time_demand=r.lead_time_demand,
            safety_stock=r.safety_stock,
            reorder_point=r.reorder_point,
            inventory_coverage_days=coverage,
            recommended_order_quantity=int(r.recommended_quantity),
            stockout_risk=r.stockout_risk,
            overstock_status="OVERSTOCKED" if is_overstocked else "HEALTHY",
            recommendation=r.recommendation,
            explanation=r.explanation
        ))
    return items

@router.get("/inventory/optimization/{product_id}")
def get_product_optimization_details(product_id: str, current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    prod = _get_product(db, product_id, _organization_id(current_user))
    if not prod:
        create_error("PRODUCT_NOT_FOUND", f"Product '{product_id}' not found.", 404)

    rec = db.query(InventoryRecommendation).filter(InventoryRecommendation.product_id == prod.id).first()
    inv = db.query(Inventory).filter(Inventory.product_id == prod.id).first()

    return {
        "product_id": prod.product_code,
        "product_name": prod.product_name,
        "category": prod.category,
        "unit_price": prod.unit_price,
        "lead_time_days": prod.lead_time_days,
        "current_inventory": inv.quantity_available if inv else 0.0,
        "quantity_on_order": inv.quantity_on_order if inv else 0.0,
        "forecast_demand_30d": rec.forecast_demand if rec else 0.0,
        "lead_time_demand": rec.lead_time_demand if rec else 0.0,
        "safety_stock": rec.safety_stock if rec else 0.0,
        "reorder_point": rec.reorder_point if rec else 0.0,
        "recommended_order_quantity": rec.recommended_quantity if rec else 0.0,
        "stockout_risk": rec.stockout_risk if rec else "LOW",
        "recommendation": rec.recommendation if rec else "NO_ACTION",
        "explanation": rec.explanation if rec else "Inventory metrics within target limits.",
    }


@router.post("/inventory/{product_id}/adjustments")
def adjust_inventory(
    product_id: str,
    payload: InventoryAdjustmentRequest,
    current_user=Depends(_require_auth),
    db: Session = Depends(get_db),
):
    """Apply an audited physical-stock adjustment without allowing negative inventory."""
    if current_user.role not in {"ADMIN", "INVENTORY_MANAGER"}:
        create_error("FORBIDDEN", "Your role cannot adjust physical inventory.", 403)
    product = _get_product(db, product_id, _organization_id(current_user))
    if not product:
        create_error("PRODUCT_NOT_FOUND", f"Product '{product_id}' not found.", 404)
    inventory = db.query(Inventory).filter(Inventory.product_id == product.id).first()
    if not inventory:
        inventory = Inventory(product_id=product.id, quantity_available=0.0, quantity_reserved=0.0, quantity_on_order=0.0)
        db.add(inventory)
        db.flush()
    before = float(inventory.quantity_available)
    after = before + payload.quantity_delta
    if after < 0:
        create_error("INVALID_REQUEST", "This adjustment would make available inventory negative.", 400)
    inventory.quantity_available = after
    db.add(InventoryTransaction(
        product_id=product.id,
        quantity_delta=payload.quantity_delta,
        quantity_before=before,
        quantity_after=after,
        reason=payload.reason.strip().upper(),
        note=payload.note.strip() if payload.note else None,
        created_by=current_user.username,
    ))
    db.commit()
    return {"product_id": product.product_code, "quantity_before": before, "quantity_after": after, "quantity_delta": payload.quantity_delta}


@router.get("/inventory/{product_id}/adjustments")
def get_inventory_adjustments(product_id: str, current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    product = _get_product(db, product_id, _organization_id(current_user))
    if not product:
        create_error("PRODUCT_NOT_FOUND", f"Product '{product_id}' not found.", 404)
    records = db.query(InventoryTransaction).filter(InventoryTransaction.product_id == product.id).order_by(InventoryTransaction.created_at.desc()).limit(50).all()
    return [{"id": row.id, "quantity_delta": row.quantity_delta, "quantity_before": row.quantity_before, "quantity_after": row.quantity_after, "reason": row.reason, "note": row.note, "created_by": row.created_by, "created_at": row.created_at.isoformat()} for row in records]


@router.post("/purchase-orders", status_code=status.HTTP_201_CREATED)
def create_purchase_order(payload: PurchaseOrderCreate, current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    if current_user.role not in {"ADMIN", "INVENTORY_MANAGER", "OPERATIONS_MANAGER"}:
        create_error("FORBIDDEN", "Your role cannot create purchase orders.", 403)
    product = _get_product(db, payload.product_id, _organization_id(current_user))
    if not product:
        create_error("PRODUCT_NOT_FOUND", f"Product '{payload.product_id}' not found.", 404)
    inventory = db.query(Inventory).filter(Inventory.product_id == product.id).first()
    if not inventory:
        inventory = Inventory(product_id=product.id, quantity_available=0.0, quantity_reserved=0.0, quantity_on_order=0.0)
        db.add(inventory)
        db.flush()
    order_number = f"PO-{datetime.utcnow():%Y%m%d}-{token_urlsafe(5).upper()}"
    order = PurchaseOrder(order_number=order_number, product_id=product.id, quantity=payload.quantity, expected_arrival_date=payload.expected_arrival_date, note=payload.note.strip() if payload.note else None, created_by=current_user.username)
    inventory.quantity_on_order += payload.quantity
    db.add(order)
    db.commit()
    return {"id": order.id, "order_number": order.order_number, "product_id": product.product_code, "product_name": product.product_name, "quantity": order.quantity, "status": order.status, "expected_arrival_date": order.expected_arrival_date.isoformat() if order.expected_arrival_date else None, "created_at": order.created_at.isoformat()}


@router.get("/purchase-orders")
def list_purchase_orders(status_filter: Optional[str] = Query(default=None, alias="status"), current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    query = db.query(PurchaseOrder).join(Product).filter(Product.organization_id == _organization_id(current_user))
    if status_filter:
        query = query.filter(PurchaseOrder.status == status_filter.upper())
    orders = query.order_by(PurchaseOrder.created_at.desc()).limit(200).all()
    return [{"id": order.id, "order_number": order.order_number, "product_id": order.product.product_code, "product_name": order.product.product_name, "quantity": order.quantity, "status": order.status, "expected_arrival_date": order.expected_arrival_date.isoformat() if order.expected_arrival_date else None, "created_by": order.created_by, "created_at": order.created_at.isoformat()} for order in orders]

# ----------------- Dashboard Summary -----------------

@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    organization_id = _organization_id(current_user)
    products = db.query(Product).filter(Product.organization_id == organization_id).all()
    total_products = len(products)

    recs = db.query(InventoryRecommendation).join(Product).filter(Product.organization_id == organization_id).all()
    reorder_count = sum(1 for r in recs if r.recommendation in ["REORDER_NOW", "REORDER_SOON"])
    high_risk_count = sum(1 for r in recs if r.stockout_risk in ["CRITICAL", "HIGH"])
    overstock_count = sum(1 for r in recs if r.recommendation == "OVERSTOCK")

    # Inventory coverage
    coverages = []
    for r in recs:
        avg_d = r.forecast_demand / 30.0 if r.forecast_demand > 0 else 0.1
        cov = r.current_inventory / avg_d
        if cov < 300:
            coverages.append(cov)
    avg_coverage = round(sum(coverages) / len(coverages), 1) if coverages else 0.0

    # Model metrics
    forecast_engine = _workspace_forecast_engine(organization_id)
    meta = forecast_engine.get_metadata()
    test_metrics = meta.get("test_metrics", {})
    avg_wape = test_metrics.get("WAPE", 16.5)

    kpis = {
        "total_products": total_products,
        "products_requiring_reorder": reorder_count,
        "high_stockout_risk": high_risk_count,
        "overstocked_products": overstock_count,
        "average_forecast_error": f"{avg_wape}% WAPE",
        "average_inventory_coverage": f"{avg_coverage} days",
    }

    # Recommendations items
    rec_items = []
    for r in recs:
        p = r.product
        avg_d = round(r.forecast_demand / 30.0, 2) if r.forecast_demand > 0 else 0.0
        cov = round(r.current_inventory / avg_d, 1) if avg_d > 0 else 999.0
        rec_items.append(InventoryRecommendationItem(
            product_id=p.product_code,
            product_name=p.product_name,
            category=p.category,
            current_inventory=r.current_inventory,
            forecast_demand=r.forecast_demand,
            average_daily_demand=avg_d,
            lead_time_days=p.lead_time_days,
            lead_time_demand=r.lead_time_demand,
            safety_stock=r.safety_stock,
            reorder_point=r.reorder_point,
            inventory_coverage_days=cov,
            recommended_order_quantity=int(r.recommended_quantity),
            stockout_risk=r.stockout_risk,
            overstock_status="OVERSTOCKED" if r.recommendation == "OVERSTOCK" else "HEALTHY",
            recommendation=r.recommendation,
            explanation=r.explanation
        ))

    # Risk breakdown
    risk_breakdown = {
        "CRITICAL": sum(1 for r in recs if r.stockout_risk == "CRITICAL"),
        "HIGH": sum(1 for r in recs if r.stockout_risk == "HIGH"),
        "MEDIUM": sum(1 for r in recs if r.stockout_risk == "MEDIUM"),
        "LOW": sum(1 for r in recs if r.stockout_risk == "LOW"),
    }

    # Category summary
    cat_map = {}
    for r in recs:
        cat = r.product.category
        if cat not in cat_map:
            cat_map[cat] = {"category": cat, "products": 0, "forecast_demand": 0.0, "current_inventory": 0.0}
        cat_map[cat]["products"] += 1
        cat_map[cat]["forecast_demand"] += r.forecast_demand
        cat_map[cat]["current_inventory"] += r.current_inventory
    category_summary = list(cat_map.values())

    # Recent runs
    model_runs = db.query(ModelRun).filter(ModelRun.organization_id == organization_id).order_by(ModelRun.timestamp.desc()).limit(5).all()
    recent_runs = [
        {
            "id": mr.id,
            "model_name": mr.model_name,
            "model_version": mr.model_version,
            "mae": mr.mae,
            "rmse": mr.rmse,
            "mape": mr.mape,
            "wape": mr.wape,
            "status": mr.status,
            "timestamp": mr.timestamp.isoformat()
        }
        for mr in model_runs
    ]

    return DashboardSummaryResponse(
        kpis=kpis,
        recommendations=rec_items,
        risk_breakdown=risk_breakdown,
        category_summary=category_summary,
        model_performance=meta,
        recent_forecast_runs=recent_runs
    )

# ----------------- Models & Registry -----------------

def _serialize_training_job(job: TrainingJob) -> Dict[str, Any]:
    return {
        "id": job.id, "status": job.status, "progress": job.progress,
        "message": job.message, "requested_by": job.requested_by,
        "model_version": job.model_version, "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


def _run_training_job(job_id: str) -> None:
    """Run a training job outside the request lifecycle and persist every outcome."""
    db = SessionLocal()
    try:
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            return
        job.status, job.progress, job.message, job.started_at = "RUNNING", 10, "Preparing training data", datetime.utcnow()
        db.commit()
        if not job.organization_id:
            raise RuntimeError("Training job has no workspace.")
        organization_id = int(job.organization_id)
        trainer = ModelTrainingPipeline(
            _workspace_read_data_path(organization_id),
            production_dir=_workspace_model_dir(organization_id),
            model_version_prefix=f"org{organization_id}-",
        )
        job.progress, job.message = 35, "Evaluating forecast candidates"
        db.commit()
        meta = trainer.run()
        job.progress, job.message = 90, "Saving champion model"
        db.commit()
        db.query(ModelRun).filter(ModelRun.organization_id == organization_id, ModelRun.status == "PRODUCTION").update({"status": "RETIRED"})
        db.add(ModelRun(
            organization_id=organization_id,
            model_name=meta["model_name"], model_version=meta["model_version"],
            training_dates=f"Historical (latest: {meta['training_date']})",
            mae=meta["test_metrics"]["MAE"], rmse=meta["test_metrics"]["RMSE"],
            mape=meta["test_metrics"]["MAPE"], wape=meta["test_metrics"]["WAPE"],
            status="PRODUCTION", artifact_path=meta["artifact_path"],
        ))
        # Training is complete, but the workspace is not ready until forecasts
        # and inventory decisions have also been persisted.
        job.status, job.progress, job.message = "RUNNING", 90, "Saving champion model"
        job.model_version = meta["model_version"]
        db.commit()
        _workspace_forecast_engine(organization_id).reload()
        job.status, job.progress, job.message = "RUNNING", 95, "Generating forecasts and inventory decisions"
        db.commit()
        _refresh_forecasts_and_recommendations(db, organization_id)
        job.status, job.progress, job.message = "SUCCEEDED", 100, "Workspace forecasts and reorder decisions are ready"
        job.completed_at = datetime.utcnow()
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if job:
            job.status, job.progress, job.message = "FAILED", 100, "Model training failed"
            job.error_message, job.completed_at = str(exc)[:2000], datetime.utcnow()
            db.commit()
        logger.exception("Training job %s failed", job_id)
    finally:
        db.close()

@router.get("/models")
def list_models(current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    runs = db.query(ModelRun).filter(ModelRun.organization_id == _organization_id(current_user)).order_by(ModelRun.timestamp.desc()).all()
    engine = _workspace_forecast_engine(_organization_id(current_user))
    meta = engine.get_metadata()

    # If database runs is empty, return metadata
    if not runs:
        return [meta]

    res = []
    for r in runs:
        res.append({
            "model_name": r.model_name,
            "model_version": r.model_version,
            "status": r.status,
            "training_dates": r.training_dates,
            "mae": r.mae,
            "rmse": r.rmse,
            "mape": r.mape,
            "wape": r.wape,
            "timestamp": r.timestamp.isoformat(),
            "artifact_path": r.artifact_path,
            "all_model_comparisons": meta.get("all_model_comparisons", [])
        })
    return res

@router.get("/models/{model_version}/metrics")
def get_model_metrics(model_version: str, current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    run = db.query(ModelRun).filter(ModelRun.model_version == model_version, ModelRun.organization_id == _organization_id(current_user)).first()
    engine = _workspace_forecast_engine(_organization_id(current_user))
    meta = engine.get_metadata()

    if run:
        return {
            "model_name": run.model_name,
            "model_version": run.model_version,
            "mae": run.mae,
            "rmse": run.rmse,
            "mape": run.mape,
            "wape": run.wape,
            "status": run.status,
            "timestamp": run.timestamp.isoformat(),
            "hyperparameters": meta.get("hyperparameters", {}),
            "features_used": meta.get("features_used", []),
            "all_model_comparisons": meta.get("all_model_comparisons", [])
        }
    if meta.get("model_version") == model_version:
        return meta

    create_error("MODEL_NOT_FOUND", f"Model version '{model_version}' not found.", 404)

@router.post("/models/train", status_code=status.HTTP_202_ACCEPTED)
def train_model_endpoint(background_tasks: BackgroundTasks, current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    if current_user.role not in ROLE_PERMISSIONS or "train_models" not in ROLE_PERMISSIONS.get(current_user.role, []):
        create_error("FORBIDDEN", "Insufficient permissions to train models.", 403)
    organization_id = _organization_id(current_user)
    active_job = db.query(TrainingJob).filter(TrainingJob.organization_id == organization_id, TrainingJob.status.in_(["QUEUED", "RUNNING"])).first()
    if active_job:
        create_error("JOB_IN_PROGRESS", "A model training job is already running.", 409)
    job = TrainingJob(id=str(uuid.uuid4()), organization_id=organization_id, requested_by=current_user.username)
    db.add(job)
    db.commit()
    background_tasks.add_task(_run_training_job, job.id)
    return _serialize_training_job(job)


@router.get("/models/jobs")
def list_training_jobs(current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    return [_serialize_training_job(job) for job in db.query(TrainingJob).filter(TrainingJob.organization_id == _organization_id(current_user)).order_by(TrainingJob.created_at.desc()).limit(20).all()]


@router.get("/models/jobs/{job_id}")
def get_training_job(job_id: str, current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id, TrainingJob.organization_id == _organization_id(current_user)).first()
    if not job:
        create_error("JOB_NOT_FOUND", f"Training job '{job_id}' not found.", 404)
    return _serialize_training_job(job)

@router.post("/models/{model_version}/promote")
def promote_model(model_version: str, current_user = Depends(_require_auth), db: Session = Depends(get_db)):
    if current_user.role not in ROLE_PERMISSIONS or "manage_models" not in ROLE_PERMISSIONS.get(current_user.role, []):
        create_error("FORBIDDEN", "Insufficient permissions.", 403)
    """Promotes a validated model version to production by swapping artifacts."""
    organization_id = _organization_id(current_user)
    run = db.query(ModelRun).filter(ModelRun.model_version == model_version, ModelRun.organization_id == organization_id).first()
    if not run:
        create_error("MODEL_NOT_FOUND", f"Model version '{model_version}' not found in registry.", 404)

    # Locate the experiment artifact for this version
    exp_dir = _workspace_model_dir(organization_id) / "experiments"
    exp_artifact = exp_dir / f"{run.model_name.lower().replace(' ', '_')}_{model_version}.joblib"
    exp_metadata = exp_dir / f"metadata_{model_version}.json"

    if not exp_artifact.exists():
        create_error("MODEL_NOT_FOUND",
                     f"Artifact for version {model_version} not found in experiments directory.", 404)

    # Retire previous production models
    db.query(ModelRun).filter(ModelRun.organization_id == organization_id, ModelRun.status == "PRODUCTION").update({"status": "RETIRED"})
    run.status = "PRODUCTION"
    db.commit()

    # Physically swap the production artifacts so the promoted version actually serves traffic
    import shutil
    prod_dir = _workspace_model_dir(organization_id)
    prod_dir.mkdir(parents=True, exist_ok=True)
    prod_artifact = prod_dir / "demand_model.joblib"
    prod_metadata = prod_dir / "metadata.json"
    shutil.copy2(exp_artifact, prod_artifact)
    if exp_metadata.exists():
        shutil.copy2(exp_metadata, prod_metadata)

    _workspace_forecast_engine(organization_id).reload()
    return {
        "status": "SUCCESS",
        "message": f"Model {model_version} promoted to PRODUCTION. Artifacts swapped.",
        "promoted_version": model_version,
        "artifact_path": str(prod_artifact),
    }

# ----------------- Data Quality -----------------

@router.post("/data/upload/preview")
async def preview_data_upload(
    file: UploadFile = File(...),
    default_inventory_level: float = Form(100.0, ge=0),
    default_lead_time_days: float = Form(7.0, ge=1, le=365),
    current_user=Depends(_require_auth),
):
    """Validate a CSV and stage it for an explicit, separate import confirmation."""
    _require_data_import_role(current_user)
    if not file.filename or not file.filename.lower().endswith(".csv"):
        create_error("INVALID_REQUEST", "Please upload a CSV file.", 400)
    content = await file.read()
    if not content:
        create_error("INVALID_REQUEST", "The uploaded file is empty.", 400)
    if len(content) > _MAX_UPLOAD_BYTES:
        create_error("INVALID_REQUEST", "Upload exceeds the 10 MB limit.", 400)

    import io
    import pandas as pd
    try:
        raw_df = pd.read_csv(io.BytesIO(content))
    except Exception:
        create_error("INVALID_REQUEST", "The file could not be read as a CSV dataset.", 400)

    normalized_df, applied_mappings, generated_fields = _normalise_upload_columns(
        raw_df, default_inventory_level, default_lead_time_days
    )
    is_valid, report = validate_dataset(normalized_df)
    preview = {
        "file_name": Path(file.filename).name,
        "raw_records": len(raw_df),
        "is_valid": is_valid,
        "validation_report": report.to_dict(),
        "applied_mappings": applied_mappings,
        "generated_fields": generated_fields,
    }
    if is_valid:
        clean_df, audit = clean_sales_data(normalized_df)
        upload_id = str(uuid.uuid4())
        pending_dir = settings.base_dir / "data" / "workspaces" / str(_organization_id(current_user)) / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        pending_path = pending_dir / f"{upload_id}.csv"
        pending_path.write_bytes(normalized_df.to_csv(index=False).encode("utf-8"))
        _pending_uploads[upload_id] = pending_path
        preview.update({"upload_id": upload_id, "cleaning_audit": audit.to_dict(), "normalized_records": len(clean_df)})
    return preview


@router.delete("/data/upload/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_data_upload(upload_id: str, current_user=Depends(_require_auth)):
    """Discard a staged CSV before it replaces the active workspace data."""
    _require_data_import_role(current_user)
    pending_path = _pending_uploads.pop(upload_id, None)
    if pending_path and pending_path.exists():
        pending_path.unlink()
    return None


@router.post("/data/upload/{upload_id}/confirm", status_code=status.HTTP_202_ACCEPTED)
def confirm_data_upload(
    upload_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(_require_auth),
    db: Session = Depends(get_db),
):
    """Promote an upload, rebuild workspace records, then train its model."""
    _require_data_import_role(current_user)
    pending_path = _pending_uploads.pop(upload_id, None)
    if not pending_path or not pending_path.exists():
        create_error("UPLOAD_NOT_FOUND", "This upload preview has expired. Upload the CSV again.", 404)
    organization_id = _organization_id(current_user)
    target_path = _workspace_data_path(organization_id)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        import shutil
        history_dir = settings.base_dir / "data" / "workspaces" / str(organization_id) / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target_path, history_dir / f"historical_sales_{datetime.utcnow():%Y%m%d_%H%M%S}.csv")
    os.replace(pending_path, target_path)
    invalidate_cleaned_cache()
    clean_df, report, audit = load_and_prepare_data(target_path)
    synced = _replace_workspace_data(db, clean_df, organization_id)
    job = TrainingJob(id=str(uuid.uuid4()), organization_id=organization_id, requested_by=current_user.username)
    db.add(job)
    db.commit()
    background_tasks.add_task(_run_training_job, job.id)
    return {
        "status": "IMPORTING",
        "message": "Data is now in your workspace. Model training and inventory decisions have started in the background.",
        "total_records": len(clean_df),
        "products_created": synced["products"],
        "sales_records_created": synced["sales_records"],
        "training_job": _serialize_training_job(job),
        "validation_report": report.to_dict(),
        "cleaning_audit": audit.to_dict(),
    }


@router.post("/workspace/use-demo-data", status_code=status.HTTP_202_ACCEPTED)
def use_demo_data(
    background_tasks: BackgroundTasks,
    current_user=Depends(_require_auth),
    db: Session = Depends(get_db),
):
    """Initialize an empty workspace with the included sample sales history."""
    _require_data_import_role(current_user)
    organization_id = _organization_id(current_user)
    if db.query(Product).filter(Product.organization_id == organization_id).count() > 0:
        create_error("WORKSPACE_ALREADY_INITIALIZED", "This workspace already has data. Import a CSV to replace it.", 409)
    source_path = settings.base_dir / "data" / "raw" / "historical_sales.csv"
    target_path = _workspace_data_path(organization_id)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not target_path.exists():
        import shutil
        shutil.copy2(source_path, target_path)
    source_path = target_path
    clean_df, report, audit = load_and_prepare_data(source_path)
    synced = _replace_workspace_data(db, clean_df, organization_id)
    job = TrainingJob(id=str(uuid.uuid4()), organization_id=organization_id, requested_by=current_user.username)
    db.add(job)
    db.commit()
    background_tasks.add_task(_run_training_job, job.id)
    return {
        "status": "IMPORTING",
        "message": "Demo workspace created. Forecasts and reorder decisions are being prepared.",
        "products_created": synced["products"],
        "sales_records_created": synced["sales_records"],
        "training_job": _serialize_training_job(job),
        "validation_report": report.to_dict(),
        "cleaning_audit": audit.to_dict(),
    }

@router.get("/data/quality")
def get_data_quality(current_user=Depends(_require_auth)):
    raw_data_path = _workspace_read_data_path(_organization_id(current_user))
    if not raw_data_path.exists():
        create_error("INTERNAL_SERVER_ERROR", "Historical data source missing.", 500)

    clean_df, val_report, clean_audit = load_and_prepare_data(raw_data_path)
    return {
        "validation_report": val_report.to_dict(),
        "cleaning_audit": clean_audit.to_dict(),
        "total_records": len(clean_df),
        "health_score": val_report.calculate_health_score(),
        "status": "EXCELLENT" if val_report.calculate_health_score() > 95 else "NEEDS_REVIEW"
    }

# ----------------- Monitoring & Drift Detection -----------------

@router.get("/monitoring/drift")
def get_drift_report(current_user=Depends(_require_auth), db: Session = Depends(get_db)):
    """Detects data/concept drift between training reference and recent production data."""
    from src.monitoring.drift_detector import DataDriftDetector

    raw_data_path = _workspace_read_data_path(_organization_id(current_user))
    if not raw_data_path.exists():
        create_error("INTERNAL_SERVER_ERROR", "Historical data source missing.", 500)

    clean_df, _, _ = load_and_prepare_data(raw_data_path)
    engine = _workspace_forecast_engine(_organization_id(current_user))
    metadata = engine.get_metadata()

    # Reference = first 70% of history (training period), current = last 30%
    from src.features.engineering import chronological_split
    _, _, full = chronological_split(clean_df, 0.70, 0.15)
    train_df, _, test_df = chronological_split(clean_df, 0.70, 0.15)

    feature_cols = ["quantity_sold", "unit_price", "lead_time_days"]
    detector = DataDriftDetector()
    report = detector.detect_dataset_drift(
        reference_df=train_df,
        current_df=test_df,
        features=feature_cols,
        target_column="quantity_sold",
    )
    return {
        "report": report.to_dict(),
        "production_model": metadata.get("model_name"),
        "production_version": metadata.get("model_version"),
        "training_date": metadata.get("training_date"),
    }

# ----------------- Auth -----------------

ROLE_PERMISSIONS = {
    "ADMIN": ["view_all", "edit_products", "train_models", "manage_system", "manage_users", "create_forecasts"],
    "DATA_SCIENTIST": ["view_all", "train_models", "evaluate_models", "manage_models", "create_forecasts"],
    "INVENTORY_MANAGER": ["view_all", "view_forecasts", "manage_inventory", "view_recommendations"],
    "OPERATIONS_MANAGER": ["view_all", "view_recommendations", "export_orders"],
    "ANALYST": ["view_all", "view_analytics", "view_performance", "create_forecasts"],
    "VIEWER": ["view_all"]
}

def _organization_slug(name: str, db: Session) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "workspace"
    base = base[:120]
    candidate, suffix = base, 2
    while db.query(Organization).filter(Organization.slug == candidate).first():
        candidate = f"{base[:130-len(str(suffix))]}-{suffix}"
        suffix += 1
    return candidate


def _profile(user: User, membership: OrganizationMembership, organization: Organization, token: str) -> UserProfile:
    return UserProfile(
        id=str(user.id), username=user.username, name=user.username, role=membership.role,
        token=token, organization_id=organization.id, organization_name=organization.name,
    )


@router.post("/auth/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def register(payload: RegistrationRequest, db: Session = Depends(get_db)):
    """Create a private organization and its first workspace administrator."""
    username = payload.username.strip()
    if db.query(User).filter(User.username == username).first():
        create_error("USERNAME_UNAVAILABLE", "That username is already in use.", 409)
    organization = Organization(name=payload.organization_name.strip(), slug=_organization_slug(payload.organization_name, db))
    user = User(username=username, password_hash=ph.hash(payload.password), role="ADMIN", is_active=True)
    db.add_all([organization, user])
    db.flush()
    membership = OrganizationMembership(organization_id=organization.id, user_id=user.id, role="ADMIN")
    raw_token = token_urlsafe(32)
    db.add_all([membership, Session(user_id=user.id, token_hash=_hash_token(raw_token), expires_at=datetime.utcnow() + timedelta(days=7))])
    db.commit()
    return _profile(user, membership, organization, raw_token)

@router.post("/auth/login", response_model=UserProfile)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not user.is_active:
        create_error("INVALID_CREDENTIALS", "Invalid username or password.", 401)
    try:
        if not ph.verify(user.password_hash, payload.password):
            create_error("INVALID_CREDENTIALS", "Invalid username or password.", 401)
    except Exception:
        create_error("INVALID_CREDENTIALS", "Invalid username or password.", 401)

    # Tokens must be unguessable.  The database stores only a SHA-256 digest,
    # so a database leak does not directly grant an active browser session.
    raw_token = token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    # Keep the session table bounded and remove credentials that can never be used.
    db.query(Session).filter(
        (Session.expires_at < datetime.utcnow()) | (Session.revoked_at.isnot(None))
    ).delete(synchronize_session=False)
    session = Session(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(session)
    db.commit()

    membership = db.query(OrganizationMembership).filter(OrganizationMembership.user_id == user.id).order_by(OrganizationMembership.id).first()
    if not membership:
        create_error("WORKSPACE_REQUIRED", "This account is not assigned to a workspace.", 403)
    organization = db.query(Organization).filter(Organization.id == membership.organization_id).first()
    return _profile(user, membership, organization, raw_token)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    """Revoke the current server-side session, making a copied token unusable."""
    session = _session_from_authorization(authorization, db)
    session.revoked_at = datetime.utcnow()
    db.commit()
    return None

@router.get("/auth/me", response_model=UserProfile)
def get_current_user(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    if not authorization:
        create_error("UNAUTHORIZED", "Authentication required.", 401)
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        create_error("UNAUTHORIZED", "Invalid authorization format.", 401)
    raw_token = parts[1]
    token_hash = _hash_token(raw_token)
    session = db.query(Session).filter(Session.token_hash == token_hash).first()
    if not session or session.revoked_at is not None or session.expires_at < datetime.utcnow():
        create_error("UNAUTHORIZED", "Session invalid, expired, or revoked.", 401)
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        create_error("UNAUTHORIZED", "User account disabled.", 401)
    membership = db.query(OrganizationMembership).filter(OrganizationMembership.user_id == user.id).order_by(OrganizationMembership.id).first()
    if not membership:
        create_error("WORKSPACE_REQUIRED", "This account is not assigned to a workspace.", 403)
    organization = db.query(Organization).filter(Organization.id == membership.organization_id).first()
    return _profile(user, membership, organization, raw_token)
