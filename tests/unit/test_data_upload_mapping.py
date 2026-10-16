import pandas as pd

from src.api.routes import _normalise_upload_columns
from src.data.validation import validate_dataset


def test_transaction_export_headers_are_mapped_to_import_schema():
    source = pd.DataFrame({
        "Product_ID": [1052], "Sale_Date": ["2023-02-03"], "Quantity_Sold": [18],
        "Product_Category": ["Furniture"], "Unit_Price": [267.22], "Sales_Amount": [5053.97],
    })
    normalized, mappings, generated = _normalise_upload_columns(source, 100, 7)
    valid, report = validate_dataset(normalized)
    assert valid is True
    assert mappings["date"] == "Sale_Date"
    assert mappings["product_id"] == "Product_ID"
    assert normalized.loc[0, "product_name"] == "Product 1052"
    assert normalized.loc[0, "inventory_level"] == 100
    assert normalized.loc[0, "lead_time_days"] == 7
    assert {"product_name", "inventory_level", "lead_time_days"}.issubset(generated)
