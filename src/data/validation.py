from typing import Tuple, List, Dict, Any
import pandas as pd
import numpy as np

REQUIRED_COLUMNS = [
    "date",
    "product_id",
    "product_name",
    "category",
    "quantity_sold",
    "unit_price",
    "revenue",
    "inventory_level",
    "lead_time_days",
]

class DataValidationReport:
    def __init__(self):
        self.total_records: int = 0
        self.missing_dates: int = 0
        self.missing_product_ids: int = 0
        self.negative_quantities: int = 0
        self.negative_prices: int = 0
        self.negative_inventory: int = 0
        self.duplicate_records: int = 0
        self.invalid_dates: int = 0
        self.missing_columns: List[str] = []
        self.warnings: List[str] = []
        self.data_coverage_start: str = ""
        self.data_coverage_end: str = ""
        self.product_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_records": self.total_records,
            "missing_dates": self.missing_dates,
            "missing_product_ids": self.missing_product_ids,
            "negative_quantities": self.negative_quantities,
            "negative_prices": self.negative_prices,
            "negative_inventory": self.negative_inventory,
            "duplicate_records": self.duplicate_records,
            "invalid_dates": self.invalid_dates,
            "missing_columns": self.missing_columns,
            "warnings": self.warnings,
            "data_coverage_start": self.data_coverage_start,
            "data_coverage_end": self.data_coverage_end,
            "product_count": self.product_count,
            "health_score": self.calculate_health_score(),
        }

    def calculate_health_score(self) -> float:
        if self.total_records == 0:
            return 0.0
        defect_count = (
            self.missing_dates
            + self.missing_product_ids
            + self.negative_prices
            + self.duplicate_records
            + self.invalid_dates
        )
        score = max(0.0, 100.0 - (defect_count / self.total_records * 100.0))
        return round(score, 1)

def validate_dataset(df: pd.DataFrame) -> Tuple[bool, DataValidationReport]:
    report = DataValidationReport()
    report.total_records = len(df)

    # Column presence
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    report.missing_columns = missing_cols
    if missing_cols:
        report.warnings.append(f"Missing required columns: {', '.join(missing_cols)}")
        return False, report

    # Duplicate check on (date, product_id)
    dup_mask = df.duplicated(subset=["date", "product_id"], keep=False)
    report.duplicate_records = int(dup_mask.sum())
    if report.duplicate_records > 0:
        report.warnings.append(f"Found {report.duplicate_records} duplicate (date, product_id) records.")

    # Missing product IDs
    report.missing_product_ids = int(df["product_id"].isna().sum() + (df["product_id"] == "").sum())

    # Date parsing check
    parsed_dates = pd.to_datetime(df["date"], errors="coerce")
    report.missing_dates = int(df["date"].isna().sum())
    report.invalid_dates = int(parsed_dates.isna().sum() - report.missing_dates)

    valid_dates = parsed_dates.dropna()
    if not valid_dates.empty:
        report.data_coverage_start = str(valid_dates.min().date())
        report.data_coverage_end = str(valid_dates.max().date())

    # Numeric checks
    report.negative_prices = int((df["unit_price"] < 0).sum())
    report.negative_quantities = int((df["quantity_sold"] < 0).sum())
    report.negative_inventory = int((df["inventory_level"] < 0).sum())

    if report.negative_prices > 0:
        report.warnings.append(f"Found {report.negative_prices} records with negative unit prices.")
    if report.negative_quantities > 0:
        report.warnings.append(f"Found {report.negative_quantities} records with negative quantities (flagged as potential returns).")

    report.product_count = int(df["product_id"].nunique())
    is_valid = len(report.missing_columns) == 0 and report.missing_product_ids == 0 and report.invalid_dates == 0
    return is_valid, report
