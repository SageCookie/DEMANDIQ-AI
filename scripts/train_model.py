import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config.settings import settings
from src.database.session import SessionLocal, Base, engine
from src.database.models import (
    Product, Sale, Inventory, Forecast, InventoryRecommendation, ModelRun
)
from src.data.ingestion import load_and_prepare_data
from src.models.trainer import ModelTrainingPipeline
from src.forecasting.engine import ForecastEngine
from src.optimization.inventory import InventoryOptimizer
from src.utils.logger import logger

def main():
    logger.info("Initializing DemandIQ AI Training and Seed Pipeline...")

    # Ensure directories
    os.makedirs(str(settings.base_dir / "models" / "production"), exist_ok=True)
    os.makedirs(str(settings.base_dir / "models" / "experiments"), exist_ok=True)

    # 1. Create database tables
    logger.info("Creating / verifying database tables...")
    Base.metadata.create_all(bind=engine)

    # 2. Ingest, validate, and clean dataset
    raw_data_path = settings.base_dir / "data" / "raw" / "historical_sales.csv"
    if not raw_data_path.exists():
        logger.info("Dataset not found. Generating default dataset...")
        from scripts.generate_dataset import generate_historical_sales_dataset
        generate_historical_sales_dataset()

    clean_df, val_report, clean_audit = load_and_prepare_data(raw_data_path)
    logger.info(f"Dataset health score: {val_report.calculate_health_score()}/100")

    # 3. Populate Database
    db = SessionLocal()
    try:
        # Populate Products and Inventory
        products_dict = {}
        for p_id, group in clean_df.groupby("product_id"):
            last_row = group.iloc[-1]
            prod = db.query(Product).filter(Product.product_code == p_id).first()
            if not prod:
                prod = Product(
                    product_code=p_id,
                    product_name=str(last_row["product_name"]),
                    category=str(last_row["category"]),
                    unit_price=float(last_row["unit_price"]),
                    lead_time_days=float(last_row["lead_time_days"]),
                    active=True
                )
                db.add(prod)
                db.flush()

            products_dict[p_id] = prod

            # Inventory
            inv = db.query(Inventory).filter(Inventory.product_id == prod.id).first()
            if not inv:
                # check on-order from known seed or 0
                inv = Inventory(
                    product_id=prod.id,
                    quantity_available=float(last_row["inventory_level"]),
                    quantity_reserved=0.0,
                    quantity_on_order=50.0 if p_id == "P002" else (30.0 if p_id == "P007" else 0.0)
                )
                db.add(inv)

        # Sales records (populate recent if empty)
        existing_sales_count = db.query(Sale).count()
        if existing_sales_count == 0:
            logger.info("Inserting sales records into database...")
            sales_to_insert = []
            for _, row in clean_df.iterrows():
                p = products_dict[row["product_id"]]
                sales_to_insert.append(Sale(
                    product_id=p.id,
                    sale_date=pd.to_datetime(row["date"]).to_pydatetime(),
                    quantity_sold=float(row["quantity_sold"]),
                    unit_price=float(row["unit_price"]),
                    revenue=float(row["revenue"])
                ))
            db.bulk_save_objects(sales_to_insert)
            db.commit()

        # 4. Train Models
        trainer = ModelTrainingPipeline(raw_data_path)
        metadata = trainer.run()

        # 5. Record Model Run in DB
        m_run = ModelRun(
            model_name=metadata["model_name"],
            model_version=metadata["model_version"],
            training_dates=f"{clean_df['date'].min().strftime('%Y-%m-%d')} to {clean_df['date'].max().strftime('%Y-%m-%d')}",
            MAE=metadata["test_metrics"]["MAE"],
            RMSE=metadata["test_metrics"]["RMSE"],
            MAPE=metadata["test_metrics"]["MAPE"],
            WAPE=metadata["test_metrics"]["WAPE"],
            status="PRODUCTION",
            artifact_path=metadata["artifact_path"]
        )
        db.add(m_run)
        db.commit()

        # 6. Generate Forecasts & Inventory Optimization
        logger.info("Generating forecasts and inventory recommendations for all active products...")
        forecast_engine = ForecastEngine.get_instance()
        forecast_engine.reload()

        optimizer = InventoryOptimizer(service_level=settings.default_service_level)

        # Clean old forecasts & recommendations
        db.query(Forecast).delete()
        db.query(InventoryRecommendation).delete()
        db.commit()

        for p_id, prod in products_dict.items():
            # Generate 30-day forecast
            forecasts = forecast_engine.generate_forecast(clean_df, p_id, horizon_days=30)
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

            # Inventory optimization
            inv = db.query(Inventory).filter(Inventory.product_id == prod.id).first()
            curr_stock = inv.quantity_available if inv else 100.0
            on_order = inv.quantity_on_order if inv else 0.0

            # Historical std dev
            p_history = clean_df[clean_df["product_id"] == p_id]["quantity_sold"]
            sigma = float(p_history.std())

            opt_res = optimizer.optimize_product(
                product_id=p_id,
                product_name=prod.product_name,
                current_inventory=curr_stock,
                on_order_quantity=on_order,
                forecast_daily_demands=daily_demands,
                lead_time_days=prod.lead_time_days,
                historical_std_dev=sigma,
                planning_horizon_days=30
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
        logger.info("Pipeline completed successfully! All models, forecasts, and recommendations generated.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error during training pipeline: {str(e)}", exc_info=True)
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    main()
