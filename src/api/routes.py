import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from src.config.settings import settings
from src.database.session import get_db
from src.database.models import (
    Product, Sale, Inventory, Forecast, InventoryRecommendation, ModelRun, User, Session
)
from src.data.ingestion import load_and_prepare_data
from src.data.validation import validate_dataset
from src.forecasting.engine import ForecastEngine
from src.optimization.inventory import InventoryOptimizer
from src.models.trainer import ModelTrainingPipeline
from src.api.schemas import (
    ProductResponse, ProductCreate, ProductUpdate,
    ForecastRequest, ForecastResponse, ForecastItem,
    InventoryRecommendationItem, DashboardSummaryResponse,
    LoginRequest, UserProfile
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
    return user

router = APIRouter(prefix="/api/v1")

# Cache cleaned dataset keyed by file mtime to avoid re-parsing the CSV on every request.
_cleaned_cache: Dict[str, Any] = {"df": None, "mtime": None}


def _get_cleaned_data():
    """Return cached cleaned DataFrame, re-loading only if the source CSV changed."""
    raw_path = settings.base_dir / "data" / "raw" / "historical_sales.csv"
    try:
        mtime = raw_path.stat().st_mtime
    except OSError:
        mtime = None
    if _cleaned_cache["df"] is None or _cleaned_cache["mtime"] != mtime:
        clean_df, _, _ = load_and_prepare_data(raw_path)
        _cleaned_cache["df"] = clean_df
        _cleaned_cache["mtime"] = mtime
    return _cleaned_cache["df"]


def invalidate_cleaned_cache():
    """Drop the cached cleaned dataset (call after retraining/re-ingestion)."""
    _cleaned_cache["df"] = None
    _cleaned_cache["mtime"] = None

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
def get_system_status(db: Session = Depends(get_db)):
    try:
        db_check = db.query(Product).count()
        db_status = "OPERATIONAL"
    except Exception as e:
        db_status = f"ERROR: {str(e)}"

    forecast_engine = ForecastEngine.get_instance()
    try:
        metadata = forecast_engine.get_metadata()
        model_status = "LOADED" if metadata.get("status") == "PRODUCTION" else "STANDBY"
    except Exception:
        model_status = "UNAVAILABLE"

    last_model_run = db.query(ModelRun).order_by(ModelRun.timestamp.desc()).first()
    last_forecast = db.query(Forecast).order_by(Forecast.generated_at.desc()).first()
    latest_sale = db.query(Sale).order_by(Sale.sale_date.desc()).first()

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
def get_products(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Product)
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

def _get_product(db: Session, product_id: str):
    """Resolve a product by product_code or numeric id safely."""
    query = db.query(Product).filter(Product.product_code == product_id)
    if product_id.isdigit():
        query = query.or_(Product.id == int(product_id))
    return query.first()


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product_detail(product_id: str, db: Session = Depends(get_db)):
    prod = _get_product(db, product_id)
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
    existing = db.query(Product).filter(Product.product_code == payload.product_code).first()
    if existing:
        create_error("INVALID_REQUEST", f"Product code '{payload.product_code}' already exists.", 400)

    prod = Product(
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
    prod = _get_product(db, product_id)
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
    prod = _get_product(db, payload.product_id)
    if not prod:
        create_error("PRODUCT_NOT_FOUND", f"Product '{payload.product_id}' not found.", 404)

    raw_data_path = settings.base_dir / "data" / "raw" / "historical_sales.csv"
    if not raw_data_path.exists():
        create_error("INTERNAL_SERVER_ERROR", "Historical dataset not initialized.", 500)

    clean_df = _get_cleaned_data()
    engine = ForecastEngine.get_instance()

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
def get_forecast_history(product_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Forecast).join(Product)
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
    db: Session = Depends(get_db)
):
    query = db.query(InventoryRecommendation).join(Product)
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
def get_product_optimization_details(product_id: str, db: Session = Depends(get_db)):
    prod = _get_product(db, product_id)
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

# ----------------- Dashboard Summary -----------------

@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    total_products = len(products)

    recs = db.query(InventoryRecommendation).join(Product).all()
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
    forecast_engine = ForecastEngine.get_instance()
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
    model_runs = db.query(ModelRun).order_by(ModelRun.timestamp.desc()).limit(5).all()
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

@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    runs = db.query(ModelRun).order_by(ModelRun.timestamp.desc()).all()
    engine = ForecastEngine.get_instance()
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
def get_model_metrics(model_version: str, db: Session = Depends(get_db)):
    run = db.query(ModelRun).filter(ModelRun.model_version == model_version).first()
    engine = ForecastEngine.get_instance()
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

@router.post("/models/train")
def train_model_endpoint(db: Session = Depends(get_db)):
    """Triggers model training, comparison and evaluation pipeline."""
    try:
        raw_data_path = settings.base_dir / "data" / "raw" / "historical_sales.csv"
        trainer = ModelTrainingPipeline(raw_data_path)
        meta = trainer.run()

        # Update DB run
        m_run = ModelRun(
            model_name=meta["model_name"],
            model_version=meta["model_version"],
            training_dates=f"Historical (latest: {meta['training_date']})",
            MAE=meta["test_metrics"]["MAE"],
            RMSE=meta["test_metrics"]["RMSE"],
            MAPE=meta["test_metrics"]["MAPE"],
            WAPE=meta["test_metrics"]["WAPE"],
            status="PRODUCTION",
            artifact_path=meta["artifact_path"]
        )
        db.add(m_run)
        db.commit()

        # Reload engine cache
        ForecastEngine.get_instance().reload()

        return {
            "status": "SUCCESS",
            "message": f"Successfully trained and evaluated models. Selected {meta['model_name']} as champion.",
            "champion_model": meta["model_name"],
            "model_version": meta["model_version"],
            "metrics": meta["test_metrics"],
            "comparisons": meta["all_model_comparisons"]
        }
    except Exception as e:
        create_error("INTERNAL_SERVER_ERROR", f"Model training failed: {str(e)}", 500)

@router.post("/models/{model_version}/promote")
def promote_model(model_version: str, current_user = Depends(_require_auth), db: Session = Depends(get_db)):
    if current_user.role not in ROLE_PERMISSIONS or "manage_models" not in ROLE_PERMISSIONS.get(current_user.role, []):
        create_error("FORBIDDEN", "Insufficient permissions.", 403)
    """Promotes a validated model version to production by swapping artifacts."""
    run = db.query(ModelRun).filter(ModelRun.model_version == model_version).first()
    if not run:
        create_error("MODEL_NOT_FOUND", f"Model version '{model_version}' not found in registry.", 404)

    # Locate the experiment artifact for this version
    exp_dir = settings.base_dir / "models" / "experiments"
    exp_artifact = exp_dir / f"{run.model_name.lower().replace(' ', '_')}_{model_version}.joblib"
    exp_metadata = exp_dir / f"metadata_{model_version}.json"

    if not exp_artifact.exists():
        create_error("MODEL_NOT_FOUND",
                     f"Artifact for version {model_version} not found in experiments directory.", 404)

    # Retire previous production models
    db.query(ModelRun).filter(ModelRun.status == "PRODUCTION").update({"status": "RETIRED"})
    run.status = "PRODUCTION"
    db.commit()

    # Physically swap the production artifacts so the promoted version actually serves traffic
    import shutil
    prod_artifact = Path(settings.model_path)
    prod_metadata = Path(settings.metadata_path)
    shutil.copy2(exp_artifact, prod_artifact)
    if exp_metadata.exists():
        shutil.copy2(exp_metadata, prod_metadata)

    ForecastEngine.get_instance().reload()
    return {
        "status": "SUCCESS",
        "message": f"Model {model_version} promoted to PRODUCTION. Artifacts swapped.",
        "promoted_version": model_version,
        "artifact_path": str(prod_artifact),
    }

# ----------------- Data Quality -----------------

@router.get("/data/quality")
def get_data_quality():
    raw_data_path = settings.base_dir / "data" / "raw" / "historical_sales.csv"
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
def get_drift_report(db: Session = Depends(get_db)):
    """Detects data/concept drift between training reference and recent production data."""
    from src.monitoring.drift_detector import DataDriftDetector

    raw_data_path = settings.base_dir / "data" / "raw" / "historical_sales.csv"
    if not raw_data_path.exists():
        create_error("INTERNAL_SERVER_ERROR", "Historical data source missing.", 500)

    clean_df, _, _ = load_and_prepare_data(raw_data_path)
    engine = ForecastEngine.get_instance()
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

    raw_token = f"demandiq_jwt_token_{user.username}_{int(time.time())}"
    token_hash = _hash_token(raw_token)
    session = Session(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(session)
    db.commit()

    return UserProfile(
        id=str(user.id),
        username=user.username,
        name=user.username,
        role=user.role,
        token=raw_token
    )

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
    return UserProfile(id=str(user.id), username=user.username, name=user.username, role=user.role, token=raw_token)
