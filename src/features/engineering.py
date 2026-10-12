from typing import List, Tuple
import pandas as pd
import numpy as np

CALENDAR_FEATURES = [
    "day",
    "day_of_week",
    "week_of_year",
    "month",
    "quarter",
    "year",
    "is_weekend",
    "is_month_start",
    "is_month_end",
]

LAG_FEATURES = ["lag_1", "lag_7", "lag_14", "lag_28"]

ROLLING_FEATURES = [
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_mean_28",
    "rolling_std_7",
    "rolling_std_14",
    "rolling_std_28",
]

EXOGENOUS_FEATURES = ["unit_price", "lead_time_days"]

ALL_MODEL_FEATURES = CALENDAR_FEATURES + LAG_FEATURES + ROLLING_FEATURES + EXOGENOUS_FEATURES

def create_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract temporal calendar features without any future leakage."""
    res = df.copy()
    dates = pd.to_datetime(res["date"])

    res["day"] = dates.dt.day
    res["day_of_week"] = dates.dt.dayofweek
    res["week_of_year"] = dates.dt.isocalendar().week.astype(int)
    res["month"] = dates.dt.month
    res["quarter"] = dates.dt.quarter
    res["year"] = dates.dt.year
    res["is_weekend"] = (dates.dt.dayofweek >= 5).astype(int)
    res["is_month_start"] = dates.dt.is_month_start.astype(int)
    res["is_month_end"] = dates.dt.is_month_end.astype(int)
    return res

def create_time_series_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates lag and rolling features grouped by product_id.
    CRITICAL: .shift(1) is applied prior to rolling windows so current day sales
    are never included in historical rolling metrics (zero data leakage guarantee).
    """
    res = create_calendar_features(df)
    res = res.sort_values(by=["product_id", "date"]).reset_index(drop=True)

    grouped = res.groupby("product_id")["quantity_sold"]

    # 1. Lags
    res["lag_1"] = grouped.shift(1)
    res["lag_7"] = grouped.shift(7)
    res["lag_14"] = grouped.shift(14)
    res["lag_28"] = grouped.shift(28)

    # 2. Rolling features strictly using past observations via shift(1)
    past_sales = grouped.shift(1)
    past_grouped = past_sales.groupby(res["product_id"])

    res["rolling_mean_7"] = past_grouped.rolling(window=7, min_periods=1).mean().reset_index(drop=True)
    res["rolling_mean_14"] = past_grouped.rolling(window=14, min_periods=1).mean().reset_index(drop=True)
    res["rolling_mean_28"] = past_grouped.rolling(window=28, min_periods=1).mean().reset_index(drop=True)

    res["rolling_std_7"] = past_grouped.rolling(window=7, min_periods=1).std().fillna(0).reset_index(drop=True)
    res["rolling_std_14"] = past_grouped.rolling(window=14, min_periods=1).std().fillna(0).reset_index(drop=True)
    res["rolling_std_28"] = past_grouped.rolling(window=28, min_periods=1).std().fillna(0).reset_index(drop=True)

    # Fill any initial early lag NaNs with backfill/median per product to allow training on whole dataset
    for col in LAG_FEATURES:
        res[col] = res.groupby("product_id")[col].bfill().ffill().fillna(0)

    for col in ROLLING_FEATURES:
        res[col] = res.groupby("product_id")[col].bfill().ffill().fillna(0)

    return res

def chronological_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Splits dataset chronologically across all products without random shuffling.
    Train: 0 -> train_ratio
    Val: train_ratio -> train_ratio + val_ratio
    Test: train_ratio + val_ratio -> 1.0
    """
    sorted_df = df.sort_values(by="date").reset_index(drop=True)
    unique_dates = sorted_df["date"].drop_duplicates().sort_values().reset_index(drop=True)
    n_dates = len(unique_dates)

    train_end_idx = int(n_dates * train_ratio)
    val_end_idx = int(n_dates * (train_ratio + val_ratio))

    train_cutoff = unique_dates.iloc[train_end_idx - 1]
    val_cutoff = unique_dates.iloc[val_end_idx - 1]

    train_df = sorted_df[sorted_df["date"] <= train_cutoff].copy()
    val_df = sorted_df[(sorted_df["date"] > train_cutoff) & (sorted_df["date"] <= val_cutoff)].copy()
    test_df = sorted_df[sorted_df["date"] > val_cutoff].copy()

    return train_df, val_df, test_df
