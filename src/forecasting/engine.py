import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import joblib
import pandas as pd
import numpy as np

from src.config.settings import settings
from src.features.engineering import create_time_series_features, ALL_MODEL_FEATURES
from src.utils.logger import logger

class ForecastEngine:
    """Loads one workspace's production model and keeps its cache private."""

    _instance: Optional["ForecastEngine"] = None

    def __init__(self, model_path: Path | str | None = None, metadata_path: Path | str | None = None):
        self.model_path = Path(model_path or settings.model_path)
        self.metadata_path = Path(metadata_path or settings.metadata_path)
        self._cached_model = None
        self._cached_metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def get_instance(cls) -> "ForecastEngine":
        if cls._instance is None:
            cls._instance = ForecastEngine()
        return cls._instance

    def get_model(self):
        if self._cached_model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Trained model not found at {self.model_path}. Please train a model first.")
            logger.info(f"Loading production model from {self.model_path}")
            self._cached_model = joblib.load(self.model_path)
        return self._cached_model

    def get_metadata(self) -> Dict[str, Any]:
        if self._cached_metadata is None:
            if self.metadata_path.exists():
                with open(self.metadata_path, "r") as f:
                    self._cached_metadata = json.load(f)
            else:
                self._cached_metadata = {
                    "model_name": "Unavailable",
                    "model_version": "v0.0.0",
                    "status": "NOT_TRAINED",
                    "training_date": None,
                    "test_metrics": {"MAE": 0, "RMSE": 0, "MAPE": 0, "WAPE": 0},
                }
        return self._cached_metadata

    def reload(self):
        """Invalidates cache to load newly promoted model."""
        self._cached_model = None
        self._cached_metadata = None

    def generate_forecast(
        self,
        historical_df: pd.DataFrame,
        product_id: str,
        horizon_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Generates day-by-day forecast for product_id across horizon_days.
        Supports 7, 14, 30, 60, 90 days.
        """
        model = self.get_model()
        metadata = self.get_metadata()
        model_version = metadata.get("model_version", "v1.0.0")

        # Filter product history
        p_df = historical_df[historical_df["product_id"] == product_id].copy()
        if p_df.empty:
            raise ValueError(f"Product ID '{product_id}' not found in historical dataset.")

        p_df["date"] = pd.to_datetime(p_df["date"])
        p_df = p_df.sort_values("date").reset_index(drop=True)

        last_date = p_df["date"].max()
        last_price = float(p_df["unit_price"].iloc[-1])
        last_lead_time = float(p_df["lead_time_days"].iloc[-1])
        p_name = str(p_df["product_name"].iloc[-1])
        category = str(p_df["category"].iloc[-1])

        # Historical standard deviation of demand for confidence intervals
        sigma = float(p_df["quantity_sold"].std())
        if np.isnan(sigma) or sigma == 0:
            sigma = 2.0

        # Forecast dates
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon_days, freq="D")
        generated_at = time.strftime("%Y-%m-%d %H:%M:%S")

        current_series = p_df.copy()
        forecasts = []

        for step_idx, f_date in enumerate(future_dates):
            # Construct row
            temp_row = pd.DataFrame([{
                "date": f_date,
                "product_id": product_id,
                "product_name": p_name,
                "category": category,
                "quantity_sold": 0.0,
                "unit_price": last_price,
                "revenue": 0.0,
                "inventory_level": 100.0,
                "lead_time_days": last_lead_time
            }])
            combined = pd.concat([current_series, temp_row], ignore_index=True)
            featured = create_time_series_features(combined)

            # Extract features for last row
            target_features = featured.iloc[[-1]][ALL_MODEL_FEATURES].fillna(0)

            # Predict
            if hasattr(model, "predict"):
                if hasattr(model, "last_demand") or hasattr(model, "avg_demand") or hasattr(model, "seasonal_map"):
                    # Baselines
                    pred_val = float(model.predict(featured.iloc[[-1]])[0])
                else:
                    pred_val = float(np.maximum(0.0, model.predict(target_features)[0]))
            else:
                pred_val = 0.0

            # Confidence bounds: expands with horizon sqrt(step_idx + 1)
            uncertainty_margin = 1.96 * sigma * np.sqrt(1 + (step_idx / 10.0))
            lower_bound = max(0.0, round(pred_val - uncertainty_margin, 2))
            upper_bound = round(pred_val + uncertainty_margin, 2)
            predicted_demand = round(pred_val, 2)

            # Update last row in current_series with predicted demand for recursive lag updates
            temp_row.loc[0, "quantity_sold"] = predicted_demand
            current_series = pd.concat([current_series, temp_row], ignore_index=True)

            forecasts.append({
                "product_id": product_id,
                "forecast_date": f_date.strftime("%Y-%m-%d"),
                "predicted_demand": predicted_demand,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "model_version": model_version,
                "generated_at": generated_at,
            })

        return forecasts
