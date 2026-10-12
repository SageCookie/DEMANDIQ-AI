import numpy as np
import pandas as pd

class NaiveForecastModel:
    """Predicts latest observed demand (lag 1)."""
    def __init__(self):
        self.name = "Naive Forecast"
        self.last_demand = {}

    def fit(self, df: pd.DataFrame):
        for p_id, group in df.groupby("product_id"):
            self.last_demand[p_id] = float(group["quantity_sold"].iloc[-1])

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in df.iterrows():
            p_id = row["product_id"]
            preds.append(self.last_demand.get(p_id, 0.0))
        return np.maximum(0.0, np.array(preds))

class MovingAverageModel:
    """Predicts average demand over last N days."""
    def __init__(self, window: int = 7):
        self.window = window
        self.name = f"Moving Average ({window}d)"
        self.avg_demand = {}

    def fit(self, df: pd.DataFrame):
        for p_id, group in df.groupby("product_id"):
            recent = group["quantity_sold"].tail(self.window)
            self.avg_demand[p_id] = float(recent.mean())

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in df.iterrows():
            p_id = row["product_id"]
            preds.append(self.avg_demand.get(p_id, 0.0))
        return np.maximum(0.0, np.array(preds))

class SeasonalNaiveModel:
    """Predicts demand matching 7-day weekly seasonality."""
    def __init__(self, season_length: int = 7):
        self.season_length = season_length
        self.name = "Seasonal Naive (7d)"
        self.seasonal_map = {}

    def fit(self, df: pd.DataFrame):
        for p_id, group in df.groupby("product_id"):
            recent_season = group["quantity_sold"].tail(self.season_length).tolist()
            self.seasonal_map[p_id] = recent_season

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in df.iterrows():
            p_id = row["product_id"]
            season = self.seasonal_map.get(p_id, [0.0])
            dow = int(pd.to_datetime(row["date"]).dayofweek) % len(season)
            preds.append(season[dow])
        return np.maximum(0.0, np.array(preds))
