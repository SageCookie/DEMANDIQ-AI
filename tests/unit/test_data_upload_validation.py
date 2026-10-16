import pandas as pd

from src.data.validation import validate_dataset


def test_upload_validation_accepts_complete_sales_schema():
    dataset = pd.DataFrame({
        "date": ["2026-01-01"], "product_id": ["SKU-1"], "product_name": ["Widget"],
        "category": ["Test"], "quantity_sold": [4], "unit_price": [10.0],
        "revenue": [40.0], "inventory_level": [20], "lead_time_days": [5],
    })
    is_valid, report = validate_dataset(dataset)
    assert is_valid is True
    assert report.calculate_health_score() == 100.0


def test_upload_validation_rejects_missing_required_column():
    dataset = pd.DataFrame({"date": ["2026-01-01"], "product_id": ["SKU-1"]})
    is_valid, report = validate_dataset(dataset)
    assert is_valid is False
    assert "product_name" in report.missing_columns
