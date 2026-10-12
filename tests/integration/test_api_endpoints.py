from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_api_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_system_status():
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["api_status"] == "ONLINE"
    assert "model_status" in data
    assert "database_status" in data

def test_get_products():
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "product_code" in first
    assert "unit_price" in first
    assert "lead_time_days" in first

def test_get_inventory_recommendations():
    response = client.get("/api/v1/inventory/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    rec = data[0]
    assert "recommendation" in rec
    assert "stockout_risk" in rec
    assert "safety_stock" in rec
    assert "reorder_point" in rec

def test_forecast_generation_endpoint():
    response = client.post("/api/v1/forecasts", json={"product_id": "P001", "horizon_days": 14})
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == "P001"
    assert data["horizon_days"] == 14
    assert len(data["forecasts"]) == 14
    assert "predicted_demand" in data["forecasts"][0]
    assert "lower_bound" in data["forecasts"][0]
    assert "upper_bound" in data["forecasts"][0]

def test_standard_error_format_on_not_found():
    response = client.get("/api/v1/products/NON_EXISTENT_SKU_9999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "PRODUCT_NOT_FOUND"
    assert "message" in data["error"]
