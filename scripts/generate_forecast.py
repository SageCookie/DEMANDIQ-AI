import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.database.session import SessionLocal
from src.database.models import Product, Forecast, Inventory, InventoryRecommendation
from src.data.ingestion import load_and_prepare_data
from src.forecasting.engine import ForecastEngine
from src.optimization.inventory import InventoryOptimizer
from src.config.settings import settings
from src.utils.logger import logger

def generate_all_forecasts(horizon_days: int = 30):
    logger.info(f"Running standalone forecast & optimization generation (horizon: {horizon_days}d)...")
    db = SessionLocal()
    try:
        from src.api.routes import invalidate_cleaned_cache
        invalidate_cleaned_cache()

        raw_data_path = settings.base_dir / "data" / "raw" / "historical_sales.csv"
        clean_df, _, _ = load_and_prepare_data(raw_data_path)

        engine = ForecastEngine.get_instance()
        optimizer = InventoryOptimizer(service_level=settings.default_service_level)

        products = db.query(Product).filter(Product.active == True).all()

        # Clear existing forecasts and recommendations
        db.query(Forecast).delete()
        db.query(InventoryRecommendation).delete()
        db.commit()

        for prod in products:
            forecasts = engine.generate_forecast(clean_df, prod.product_code, horizon_days=horizon_days)
            daily_demands = [f["predicted_demand"] for f in forecasts]

            for f_item in forecasts:
                f_date_obj = datetime.strptime(f_item["forecast_date"], "%Y-%m-%d")
                db.add(Forecast(
                    product_id=prod.id,
                    forecast_date=f_date_obj,
                    predicted_demand=float(f_item["predicted_demand"]),
                    lower_bound=float(f_item["lower_bound"]),
                    upper_bound=float(f_item["upper_bound"]),
                    model_version=str(f_item["model_version"])
                ))

            inv = db.query(Inventory).filter(Inventory.product_id == prod.id).first()
            curr_stock = inv.quantity_available if inv else 100.0
            on_order = inv.quantity_on_order if inv else 0.0

            p_history = clean_df[clean_df["product_id"] == prod.product_code]["quantity_sold"]
            sigma = float(p_history.std())

            opt_res = optimizer.optimize_product(
                product_id=prod.product_code,
                product_name=prod.product_name,
                current_inventory=curr_stock,
                on_order_quantity=on_order,
                forecast_daily_demands=daily_demands,
                lead_time_days=prod.lead_time_days,
                historical_std_dev=sigma,
                planning_horizon_days=horizon_days
            )

            db.add(InventoryRecommendation(
                product_id=prod.id,
                current_inventory=opt_res["current_inventory"],
                forecast_demand=opt_res["forecast_demand"],
                lead_time_demand=opt_res["lead_time_demand"],
                safety_stock=opt_res["safety_stock"],
                reorder_point=opt_res["reorder_point"],
                recommended_quantity=opt_res["recommended_order_quantity"],
                stockout_risk=opt_res["stockout_risk"],
                recommendation=opt_res["recommendation"],
                explanation=opt_res["explanation"]
            ))

        db.commit()
        logger.info(f"Forecasts and recommendations updated for {len(products)} products.")
    finally:
        db.close()

if __name__ == "__main__":
    generate_all_forecasts()
