import pytest
from src.optimization.inventory import InventoryOptimizer

def test_business_logic_example():
    """
    Test case specified in documentation:
    Average Daily Demand = 20
    Lead Time = 7
    Safety Stock = 30
    Lead-Time Demand = 20 * 7 = 140
    Reorder Point = 140 + 30 = 170
    If current inventory = 80 -> product is below ROP and must be identified for replenishment.
    """
    optimizer = InventoryOptimizer(service_level=0.95)

    # 30 days horizon with daily demand 20 = 600 total demand
    daily_demands = [20.0] * 30

    result = optimizer.optimize_product(
        product_id="TEST_PROD",
        product_name="Test Widget",
        current_inventory=80.0,
        on_order_quantity=0.0,
        forecast_daily_demands=daily_demands,
        lead_time_days=7.0,
        historical_std_dev=6.89,  # yields safety stock ~30 with Z=1.645 and sqrt(7)
        planning_horizon_days=30
    )

    assert result["lead_time_demand"] == 140.0
    assert result["reorder_point"] >= 165.0  # ~170
    assert result["current_inventory"] == 80.0
    assert result["recommendation"] in ["REORDER_NOW", "REORDER_SOON"]
    assert result["recommended_order_quantity"] > 0
    assert result["stockout_risk"] in ["HIGH", "CRITICAL"]
    assert "reorder" in result["explanation"].lower() or "risk" in result["explanation"].lower()

def test_order_quantity_clamping_to_zero():
    """Ensure recommended order quantity is clamped to 0 when inventory exceeds target stock."""
    optimizer = InventoryOptimizer(service_level=0.95)
    daily_demands = [10.0] * 30  # 300 target demand

    result = optimizer.optimize_product(
        product_id="TEST_OVERSTOCK",
        product_name="Surplus Item",
        current_inventory=800.0,  # Far above target stock
        on_order_quantity=100.0,
        forecast_daily_demands=daily_demands,
        lead_time_days=7.0,
        planning_horizon_days=30
    )

    assert result["recommended_order_quantity"] == 0
    assert result["recommendation"] == "OVERSTOCK"
    assert result["overstock_status"] == "OVERSTOCKED"
    assert result["excess_inventory"] > 0

def test_zero_demand_coverage_handling():
    """Verify zero division is safely handled when average daily demand is 0."""
    optimizer = InventoryOptimizer(service_level=0.95)
    daily_demands = [0.0] * 30

    result = optimizer.optimize_product(
        product_id="TEST_ZERO",
        product_name="Zero Sales Item",
        current_inventory=50.0,
        on_order_quantity=0.0,
        forecast_daily_demands=daily_demands,
        lead_time_days=7.0,
        planning_horizon_days=30
    )

    assert result["average_daily_demand"] == 0.0
    assert result["inventory_coverage_days"] == 999.0
    assert result["recommended_order_quantity"] == 0
