import math
from typing import Dict, Any, List
from scipy.stats import norm
from src.config.settings import settings

def get_z_score(service_level: float = 0.95) -> float:
    """Computes Z-factor for standard normal distribution at specified service level."""
    try:
        return float(norm.ppf(service_level))
    except Exception:
        # Fallback to standard 95% = 1.6449
        return 1.6449

class InventoryOptimizer:
    def __init__(self, service_level: float = settings.default_service_level):
        self.service_level = service_level
        self.z_factor = get_z_score(service_level)

    def optimize_product(
        self,
        product_id: str,
        product_name: str,
        current_inventory: float,
        on_order_quantity: float,
        forecast_daily_demands: List[float],
        lead_time_days: float,
        historical_std_dev: float = 0.0,
        planning_horizon_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculates all inventory metrics, safety stock, reorder point,
        recommended order quantity, stockout risk, overstock status, and explainability.
        """
        lead_time = max(1.0, float(lead_time_days))
        curr_inv = max(0.0, float(current_inventory))
        on_order = max(0.0, float(on_order_quantity))

        # Forecast demand for planning horizon
        horizon_demand = sum(forecast_daily_demands[:planning_horizon_days]) if forecast_daily_demands else 0.0
        avg_daily_demand = (horizon_demand / max(1, planning_horizon_days)) if horizon_demand > 0 else 0.0

        # Demand std dev
        sigma = historical_std_dev if historical_std_dev > 0 else (avg_daily_demand * 0.25)
        if sigma <= 0:
            sigma = 1.0

        # 1. Lead-Time Demand = Average Daily Demand * Lead Time
        lead_time_demand = round(avg_daily_demand * lead_time, 1)

        # 2. Safety Stock = Z * sigma * sqrt(L)
        safety_stock = round(self.z_factor * sigma * math.sqrt(lead_time), 1)

        # 3. Reorder Point = Lead-Time Demand + Safety Stock
        reorder_point = round(lead_time_demand + safety_stock, 1)

        # 4. Target Stock = Forecast Demand + Safety Stock
        target_stock = round(horizon_demand + safety_stock, 1)

        # 5. Inventory Coverage Days = Current Inventory / Average Daily Demand
        if avg_daily_demand > 0.001:
            inventory_coverage_days = round(curr_inv / avg_daily_demand, 1)
        else:
            inventory_coverage_days = 999.0  # Zero/negligible daily demand

        # 6. Recommended Order Quantity = Target Stock - Current Inventory - On-Order Quantity
        raw_order_qty = target_stock - curr_inv - on_order
        recommended_order_quantity = max(0.0, round(raw_order_qty, 0))

        # 7. Stockout Risk and Recommendation Classification
        effective_stock = curr_inv + on_order
        days_until_stockout = curr_inv / avg_daily_demand if avg_daily_demand > 0.001 else 999.0

        # Overstock detection: stock covers significantly more than target demand + safety stock
        is_overstocked = (curr_inv > target_stock * 1.35 and curr_inv > 20) or (inventory_coverage_days > max(60.0, lead_time * 4))
        excess_inventory = max(0.0, round(curr_inv - target_stock, 1)) if is_overstocked else 0.0

        # CRITICAL: Projected inventory reaches zero before replenishment arrives
        if curr_inv <= 0 or days_until_stockout < lead_time:
            stockout_risk = "CRITICAL"
            recommendation = "REORDER_NOW"
            reason = (
                f"CRITICAL risk: Available inventory ({int(curr_inv)} units) provides only {inventory_coverage_days} days coverage, "
                f"which will exhaust before supplier replenishment lead time ({int(lead_time)} days). "
                f"Immediate expedited purchase order of {int(recommended_order_quantity)} units required."
            )
        # HIGH: Inventory approaches or breaches safety stock
        elif curr_inv <= (safety_stock + lead_time_demand * 0.5) or curr_inv <= safety_stock:
            stockout_risk = "HIGH"
            recommendation = "REORDER_NOW"
            reason = (
                f"HIGH risk: Current stock ({int(curr_inv)} units) is approaching safety buffer ({safety_stock} units) "
                f"and is below reorder point ({reorder_point} units). Projected lead-time demand is {lead_time_demand} units. "
                f"Recommended purchase order of {int(recommended_order_quantity)} units to prevent stockout."
            )
        # MEDIUM: Inventory is below reorder point / preferred target
        elif curr_inv <= reorder_point:
            stockout_risk = "MEDIUM"
            recommendation = "REORDER_SOON"
            reason = (
                f"MEDIUM risk: Stock ({int(curr_inv)} units) is below reorder threshold ({reorder_point} units). "
                f"Place order of {int(recommended_order_quantity)} units within next 48 hours to maintain safe operational buffer."
            )
        elif is_overstocked:
            stockout_risk = "LOW"
            recommendation = "OVERSTOCK"
            reason = (
                f"OVERSTOCK alert: Inventory ({int(curr_inv)} units) exceeds target stock ({target_stock} units) by ~{excess_inventory} units, "
                f"providing {inventory_coverage_days} days of coverage. Defer purchase orders and evaluate promotional liquidation."
            )
        elif curr_inv <= reorder_point * 1.25:
            stockout_risk = "LOW"
            recommendation = "MONITOR"
            reason = (
                f"Stock is currently stable ({int(curr_inv)} units vs ROP {reorder_point} units), "
                f"providing {inventory_coverage_days} days coverage. No order needed today; monitor incoming sales velocity."
            )
        else:
            stockout_risk = "LOW"
            recommendation = "NO_ACTION"
            reason = (
                f"Optimal inventory level. Stock ({int(curr_inv)} units) comfortably exceeds reorder point ({reorder_point} units) "
                f"with {inventory_coverage_days} days coverage across current demand forecasts."
            )

        return {
            "product_id": product_id,
            "product_name": product_name,
            "current_inventory": curr_inv,
            "on_order_quantity": on_order,
            "forecast_demand": round(horizon_demand, 1),
            "average_daily_demand": round(avg_daily_demand, 2),
            "lead_time_days": lead_time,
            "lead_time_demand": lead_time_demand,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "target_stock": target_stock,
            "inventory_coverage_days": inventory_coverage_days,
            "recommended_order_quantity": int(recommended_order_quantity),
            "stockout_risk": stockout_risk,
            "overstock_status": "OVERSTOCKED" if is_overstocked else "HEALTHY",
            "excess_inventory": excess_inventory,
            "recommendation": recommendation,
            "explanation": reason,
            "service_level": self.service_level,
        }
