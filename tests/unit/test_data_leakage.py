import pandas as pd
import numpy as np
from src.features.engineering import create_time_series_features, chronological_split

def test_no_data_leakage_in_features():
    """
    CRITICAL ML REQUIREMENT:
    Verify that rolling and lag features do NOT leak current or future values.
    Specifically:
    1. A spike in day T's quantity_sold should NOT alter day T's rolling_mean or lag_1.
    2. Only day T+1 onwards should reflect the change.
    """
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    base_data = pd.DataFrame({
        "date": dates,
        "product_id": "P001",
        "product_name": "Test",
        "category": "TestCat",
        "quantity_sold": [10.0] * 10,
        "unit_price": 50.0,
        "revenue": 500.0,
        "inventory_level": 100.0,
        "lead_time_days": 7.0
    })

    # Case A: flat sales of 10
    feat_a = create_time_series_features(base_data)

    # Case B: introduce huge spike on day 5 (index 4)
    spiked_data = base_data.copy()
    spiked_data.loc[4, "quantity_sold"] = 9999.0
    feat_b = create_time_series_features(spiked_data)

    # On day 5 (index 4), the features lag_1 and rolling_mean_7 MUST BE IDENTICAL in both cases
    # because they must only reflect past observations!
    assert feat_a.loc[4, "lag_1"] == feat_b.loc[4, "lag_1"], "Data leakage detected: lag_1 changed on spike day!"
    assert feat_a.loc[4, "rolling_mean_7"] == feat_b.loc[4, "rolling_mean_7"], "Data leakage detected: rolling_mean_7 changed on spike day!"

    # On day 6 (index 5), the spike should now appear in lag_1
    assert feat_b.loc[5, "lag_1"] == 9999.0

def test_chronological_split_strict_ordering():
    """Verify that train, validation, and test splits strictly preserve temporal ordering without leakage."""
    dates = pd.date_range("2026-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "date": dates,
        "product_id": "P001",
        "quantity_sold": np.random.randint(10, 50, size=100)
    })

    train_df, val_df, test_df = chronological_split(df, train_ratio=0.70, val_ratio=0.15)

    assert train_df["date"].max() < val_df["date"].min(), "Train/Val temporal boundary violated!"
    assert val_df["date"].max() < test_df["date"].min(), "Val/Test temporal boundary violated!"
    assert len(train_df) + len(val_df) + len(test_df) == 100
