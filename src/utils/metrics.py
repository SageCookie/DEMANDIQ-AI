import numpy as np

def calculate_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Error"""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))

def calculate_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Error"""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray, epsilon: float = 1e-5) -> float:
    """Mean Absolute Percentage Error (handles zero demand by avoiding division by zero)"""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    # Filter where actual is non-zero, or use epsilon
    mask = y_true > epsilon
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)

def calculate_wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Weighted Absolute Percentage Error - ideal for zero-heavy intermittent demand"""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    sum_actual = np.sum(y_true)
    if sum_actual == 0:
        return 0.0
    return float((np.sum(np.abs(y_true - y_pred)) / sum_actual) * 100.0)

def calculate_smape(y_true: np.ndarray, y_pred: np.ndarray, epsilon: float = 1e-5) -> float:
    """Symmetric Mean Absolute Percentage Error"""
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0 + epsilon
    return float(np.mean(np.abs(y_pred - y_true) / denominator) * 100.0)

def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Comprehensive evaluation dictionary"""
    return {
        "MAE": round(calculate_mae(y_true, y_pred), 4),
        "RMSE": round(calculate_rmse(y_true, y_pred), 4),
        "MAPE": round(calculate_mape(y_true, y_pred), 2),
        "WAPE": round(calculate_wape(y_true, y_pred), 2),
        "sMAPE": round(calculate_smape(y_true, y_pred), 2),
    }
