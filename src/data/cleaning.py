from typing import Tuple, Dict, Any, List
import pandas as pd
import numpy as np
from src.utils.logger import logger

class CleaningAudit:
    def __init__(self):
        self.rows_before: int = 0
        self.rows_after: int = 0
        self.duplicates_removed: int = 0
        self.missing_imputed: int = 0
        self.dates_corrected: int = 0
        self.zero_days_filled: int = 0
        self.logs: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rows_before": self.rows_before,
            "rows_after": self.rows_after,
            "duplicates_removed": self.duplicates_removed,
            "missing_imputed": self.missing_imputed,
            "dates_corrected": self.dates_corrected,
            "zero_days_filled": self.zero_days_filled,
            "logs": self.logs,
        }

def clean_sales_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, CleaningAudit]:
    audit = CleaningAudit()
    audit.rows_before = len(df)
    clean_df = df.copy()

    # 1. Date conversion
    clean_df["date"] = pd.to_datetime(clean_df["date"], errors="coerce")
    invalid_dates_count = int(clean_df["date"].isna().sum())
    if invalid_dates_count > 0:
        audit.logs.append(f"Dropped {invalid_dates_count} rows with unparseable dates.")
        clean_df = clean_df.dropna(subset=["date"])
        audit.dates_corrected += invalid_dates_count

    # 2. String trimming & product sanitization
    clean_df["product_id"] = clean_df["product_id"].astype(str).str.strip()
    clean_df["product_name"] = clean_df["product_name"].astype(str).str.strip()
    clean_df["category"] = clean_df["category"].astype(str).str.strip()
    clean_df = clean_df[clean_df["product_id"] != ""]

    # 3. Numeric conversion and negative checks
    for col in ["quantity_sold", "unit_price", "revenue", "inventory_level", "lead_time_days"]:
        if col in clean_df.columns:
            clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce")

    # If quantity is negative, clamp to 0 or treat as return
    neg_qty = (clean_df["quantity_sold"] < 0).sum()
    if neg_qty > 0:
        audit.logs.append(f"Sanitized {neg_qty} negative quantity records to zero.")
        clean_df.loc[clean_df["quantity_sold"] < 0, "quantity_sold"] = 0

    # Ensure non-negative prices
    clean_df.loc[clean_df["unit_price"] < 0, "unit_price"] = 0.0

    # Recompute revenue if missing/inconsistent
    clean_df["revenue"] = (clean_df["quantity_sold"] * clean_df["unit_price"]).round(2)

    # Lead time default fallback
    clean_df["lead_time_days"] = clean_df["lead_time_days"].fillna(7).clip(lower=1)

    # 4. Deduplication by date and product_id (aggregate quantity_sold and average price)
    dups = clean_df.duplicated(subset=["date", "product_id"], keep=False).sum()
    if dups > 0:
        audit.logs.append(f"Aggregated {dups} duplicate date-product transactions.")
        audit.duplicates_removed = int(dups)
        clean_df = clean_df.groupby(["date", "product_id", "product_name", "category"], as_index=False).agg({
            "quantity_sold": "sum",
            "unit_price": "mean",
            "revenue": "sum",
            "inventory_level": "last",
            "lead_time_days": "mean"
        })

    # 5. Build Complete Time Index per product
    # Distinguish true zero sales from missing observation
    all_product_dfs = []
    min_date = clean_df["date"].min()
    max_date = clean_df["date"].max()

    if pd.notna(min_date) and pd.notna(max_date):
        full_date_range = pd.date_range(start=min_date, end=max_date, freq="D")
        for p_id, group in clean_df.groupby("product_id"):
            p_name = group["product_name"].iloc[0]
            cat = group["category"].iloc[0]
            avg_price = group["unit_price"].median()
            lead_time = group["lead_time_days"].median()

            group = group.set_index("date").reindex(full_date_range)
            group.index.name = "date"
            group = group.reset_index()

            # Fill attributes
            group["product_id"] = p_id
            group["product_name"] = p_name
            group["category"] = cat
            group["unit_price"] = group["unit_price"].fillna(avg_price)
            group["lead_time_days"] = group["lead_time_days"].fillna(lead_time)

            # Missing sales days are true 0 sales
            missing_days = group["quantity_sold"].isna().sum()
            audit.zero_days_filled += int(missing_days)
            group["quantity_sold"] = group["quantity_sold"].fillna(0)
            group["revenue"] = (group["quantity_sold"] * group["unit_price"]).round(2)

            # Forward fill inventory or default
            group["inventory_level"] = group["inventory_level"].ffill().bfill().fillna(100)

            all_product_dfs.append(group)

        if all_product_dfs:
            clean_df = pd.concat(all_product_dfs, ignore_index=True)

    # 6. Chronological sort
    clean_df = clean_df.sort_values(by=["date", "product_id"]).reset_index(drop=True)
    audit.rows_after = len(clean_df)
    audit.logs.append(f"Successfully cleaned dataset: {audit.rows_before} raw records -> {audit.rows_after} normalized daily records.")
    logger.info(f"Data cleaning finished: {audit.rows_after} records.")
    return clean_df, audit
