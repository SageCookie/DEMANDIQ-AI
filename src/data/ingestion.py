from pathlib import Path
from typing import Tuple, Optional
import pandas as pd
from src.data.validation import validate_dataset, DataValidationReport
from src.data.cleaning import clean_sales_data, CleaningAudit
from src.utils.logger import logger

def load_and_prepare_data(file_path: Path | str) -> Tuple[pd.DataFrame, DataValidationReport, CleaningAudit]:
    """Loads raw data, performs validation, and runs cleaning pipeline."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}")

    logger.info(f"Loading raw dataset from {path}")
    raw_df = pd.read_csv(path)

    is_valid, validation_report = validate_dataset(raw_df)
    clean_df, cleaning_audit = clean_sales_data(raw_df)

    return clean_df, validation_report, cleaning_audit
