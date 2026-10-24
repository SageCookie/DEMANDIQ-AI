import time
import json
from pathlib import Path
from typing import Dict, Any, Tuple
import joblib
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

from src.features.engineering import (
    create_time_series_features,
    chronological_split,
    ALL_MODEL_FEATURES,
)
from src.models.baselines import NaiveForecastModel, MovingAverageModel, SeasonalNaiveModel
from src.utils.metrics import evaluate_predictions
from src.utils.logger import logger
from src.config.settings import settings

class ModelTrainingPipeline:
    def __init__(self, data_path: Path | str, production_dir: Path | str | None = None, model_version_prefix: str = ""):
        self.data_path = Path(data_path)
        self.production_dir = Path(production_dir or Path(settings.model_path).parent)
        self.experiments_dir = self.production_dir / "experiments"
        self.model_version_prefix = model_version_prefix
        self.production_dir.mkdir(parents=True, exist_ok=True)
        self.experiments_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        logger.info("Initiating model training pipeline...")
        df = pd.read_csv(self.data_path)
        df["date"] = pd.to_datetime(df["date"])

        # 1. Feature Engineering
        featured_df = create_time_series_features(df)

        # 2. Chronological Split (70% train, 15% validation, 15% test)
        train_df, val_df, test_df = chronological_split(featured_df, 0.70, 0.15)
        logger.info(f"Split sizes: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")

        X_train = train_df[ALL_MODEL_FEATURES].fillna(0)
        y_train = train_df["quantity_sold"].values

        X_val = val_df[ALL_MODEL_FEATURES].fillna(0)
        y_val = val_df["quantity_sold"].values

        X_test = test_df[ALL_MODEL_FEATURES].fillna(0)
        y_test = test_df["quantity_sold"].values

        # 3. Model Candidates
        models = {
            "Naive Forecast": NaiveForecastModel(),
            "Moving Average": MovingAverageModel(window=7),
            "Seasonal Naive": SeasonalNaiveModel(season_length=7),
            "Linear Regression": Ridge(alpha=1.0),
            "Random Forest": RandomForestRegressor(n_estimators=60, max_depth=12, random_state=42, n_jobs=-1),
            "XGBoost": XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.08, random_state=42, n_jobs=-1),
        }

        comparison_results = []
        trained_instances = {}

        for name, model in models.items():
            t0 = time.time()
            if hasattr(model, "fit"):
                if isinstance(model, (NaiveForecastModel, MovingAverageModel, SeasonalNaiveModel)):
                    model.fit(train_df)
                    preds_val = model.predict(val_df)
                else:
                    model.fit(X_train, y_train)
                    preds_val = np.maximum(0.0, model.predict(X_val))
            t_elapsed = round((time.time() - t0) * 1000, 2)  # ms

            metrics_val = evaluate_predictions(y_val, preds_val)
            metrics_val["training_time_ms"] = t_elapsed
            metrics_val["model_name"] = name

            comparison_results.append(metrics_val)
            trained_instances[name] = model
            logger.info(f"Evaluated {name} on Val set -> MAE: {metrics_val['MAE']}, RMSE: {metrics_val['RMSE']}, WAPE: {metrics_val['WAPE']}%")

        # 4. Model Selection based on lowest Validation WAPE (or MAE)
        best_candidate = min(comparison_results, key=lambda x: (x["WAPE"], x["MAE"]))
        best_model_name = best_candidate["model_name"]
        logger.info(f"Selected best candidate: {best_model_name}")

        # 5. Retrain best model on Train + Val combined, and test on holdout Test set
        train_val_df = pd.concat([train_df, val_df], ignore_index=True)
        X_train_val = train_val_df[ALL_MODEL_FEATURES].fillna(0)
        y_train_val = train_val_df["quantity_sold"].values

        final_model = models[best_model_name]
        t0 = time.time()
        if isinstance(final_model, (NaiveForecastModel, MovingAverageModel, SeasonalNaiveModel)):
            final_model.fit(train_val_df)
            test_preds = final_model.predict(test_df)
        else:
            final_model.fit(X_train_val, y_train_val)
            test_preds = np.maximum(0.0, final_model.predict(X_test))
        final_training_time_ms = round((time.time() - t0) * 1000, 2)

        test_metrics = evaluate_predictions(y_test, test_preds)
        test_metrics["training_time_ms"] = final_training_time_ms

        # 6. Save model artifact and metadata
        model_version = f"{self.model_version_prefix}v1.{int(time.time()) % 100000}"
        artifact_filename = f"{best_model_name.lower().replace(' ', '_')}_{model_version}.joblib"
        exp_artifact_path = self.experiments_dir / artifact_filename
        prod_artifact_path = self.production_dir / "demand_model.joblib"
        prod_metadata_path = self.production_dir / "metadata.json"

        # Save to experiment & production
        joblib.dump(final_model, exp_artifact_path)
        joblib.dump(final_model, prod_artifact_path)

        metadata = {
            "model_name": best_model_name,
            "model_version": model_version,
            "status": "PRODUCTION",
            "training_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dataset_version": "1.0.0",
            "feature_version": "1.0.0",
            "features_used": ALL_MODEL_FEATURES,
            "train_records": len(train_val_df),
            "test_records": len(test_df),
            "test_metrics": test_metrics,
            "validation_metrics": best_candidate,
            "all_model_comparisons": comparison_results,
            "hyperparameters": getattr(final_model, "get_params", lambda: {})(),
            "artifact_path": str(prod_artifact_path),
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        # Save metadata to production and experiment
        with open(prod_metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        exp_metadata_path = self.experiments_dir / f"metadata_{model_version}.json"
        with open(exp_metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(f"Model successfully saved to {prod_artifact_path} with version {model_version}")
        return metadata
