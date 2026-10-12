import math
import random
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

import os

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
os.makedirs(str(OUTPUT_DIR), exist_ok=True)
CSV_FILE = OUTPUT_DIR / "historical_sales.csv"

PRODUCTS = [
    {
        "id": "P001",
        "name": "Quantum Wireless Earbuds Pro",
        "category": "Consumer Electronics",
        "price": 129.99,
        "lead_time": 7,
        "base_daily": 24.0,
        "weekly_pattern": [0.9, 0.95, 1.0, 1.05, 1.25, 1.35, 1.1],
        "inventory_level": 82,   # Below reorder point -> REORDER_NOW
        "on_order": 0,
    },
    {
        "id": "P002",
        "name": "AeroLite Titanium Laptop Stand",
        "category": "Consumer Electronics",
        "price": 64.50,
        "lead_time": 10,
        "base_daily": 16.0,
        "weekly_pattern": [1.0, 1.0, 1.05, 1.1, 1.15, 0.85, 0.85],
        "inventory_level": 140,  # Approaching ROP -> REORDER_SOON
        "on_order": 50,
    },
    {
        "id": "P003",
        "name": "Precision Stepper Motor 24V",
        "category": "Industrial",
        "price": 85.00,
        "lead_time": 14,
        "base_daily": 12.0,
        "weekly_pattern": [1.3, 1.25, 1.2, 1.15, 1.1, 0.3, 0.2],
        "inventory_level": 45,   # Critical stockout risk
        "on_order": 0,
    },
    {
        "id": "P004",
        "name": "Vortex High-Torque Servo Actuator",
        "category": "Industrial",
        "price": 210.00,
        "lead_time": 21,
        "base_daily": 6.5,
        "weekly_pattern": [1.2, 1.2, 1.1, 1.1, 1.0, 0.2, 0.1],
        "inventory_level": 190,  # Healthy
        "on_order": 0,
    },
    {
        "id": "P005",
        "name": "OmniGrip Ergonomic Workwear Glove",
        "category": "Apparel & Gear",
        "price": 24.99,
        "lead_time": 5,
        "base_daily": 42.0,
        "weekly_pattern": [1.2, 1.2, 1.15, 1.1, 1.05, 0.5, 0.4],
        "inventory_level": 850,  # OVERSTOCK
        "on_order": 0,
    },
    {
        "id": "P006",
        "name": "ThermaShield All-Weather Outerwear",
        "category": "Apparel & Gear",
        "price": 145.00,
        "lead_time": 12,
        "base_daily": 15.0,
        "weekly_pattern": [0.85, 0.9, 0.95, 1.05, 1.3, 1.5, 1.35],
        "inventory_level": 230,  # Stable
        "on_order": 0,
    },
    {
        "id": "P007",
        "name": "SmartSensor Environmental Monitor",
        "category": "Consumer Electronics",
        "price": 49.00,
        "lead_time": 7,
        "base_daily": 19.5,
        "weekly_pattern": [1.0, 1.0, 1.0, 1.05, 1.15, 1.1, 0.95],
        "inventory_level": 60,   # High risk
        "on_order": 30,
    },
    {
        "id": "P008",
        "name": "Acoustic Noise-Canceling Desk Pod",
        "category": "Home & Office",
        "price": 320.00,
        "lead_time": 18,
        "base_daily": 4.0,
        "weekly_pattern": [1.1, 1.15, 1.1, 1.05, 1.0, 0.4, 0.3],
        "inventory_level": 95,   # Healthy
        "on_order": 0,
    },
    {
        "id": "P009",
        "name": "HydroPure Water Filtration Core",
        "category": "Industrial",
        "price": 175.00,
        "lead_time": 14,
        "base_daily": 8.0,
        "weekly_pattern": [1.2, 1.15, 1.1, 1.05, 1.0, 0.4, 0.3],
        "inventory_level": 135,  # Monitor
        "on_order": 0,
    },
    {
        "id": "P010",
        "name": "UltraCompact GaN 140W Fast Charger",
        "category": "Consumer Electronics",
        "price": 79.99,
        "lead_time": 6,
        "base_daily": 30.0,
        "weekly_pattern": [0.95, 0.95, 1.0, 1.05, 1.25, 1.35, 1.1],
        "inventory_level": 90,   # REORDER_NOW
        "on_order": 0,
    },
    {
        "id": "P011",
        "name": "Titanium Hex Fasteners (500-pack)",
        "category": "Industrial",
        "price": 38.50,
        "lead_time": 8,
        "base_daily": 22.0,
        "weekly_pattern": [1.3, 1.25, 1.2, 1.1, 1.0, 0.2, 0.15],
        "inventory_level": 650,  # OVERSTOCK
        "on_order": 0,
    },
    {
        "id": "P012",
        "name": "Modular Magnetic Cable Hub",
        "category": "Home & Office",
        "price": 19.99,
        "lead_time": 4,
        "base_daily": 35.0,
        "weekly_pattern": [0.9, 0.95, 1.0, 1.1, 1.25, 1.3, 1.15],
        "inventory_level": 210,  # Stable
        "on_order": 0,
    },
]

def generate_historical_sales_dataset(num_days: int = 365) -> pd.DataFrame:
    random.seed(42)
    np.random.seed(42)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=num_days)

    records = []

    for p in PRODUCTS:
        curr_date = start_date
        simulated_inv = p["inventory_level"] + random.randint(100, 300)

        for day_idx in range(num_days):
            dow = curr_date.weekday()
            day_of_year = curr_date.timetuple().tm_yday

            # Base demand + weekly pattern + annual seasonality curve
            annual_seasonality = 1.0 + 0.18 * math.sin(2 * math.pi * (day_of_year - 80) / 365.25)
            dow_multiplier = p["weekly_pattern"][dow]

            # Slight trend (+10% over the year)
            trend_multiplier = 1.0 + (day_idx / num_days) * 0.12

            # Random Poisson/Normal noise
            expected_demand = p["base_daily"] * dow_multiplier * annual_seasonality * trend_multiplier
            demand_noise = np.random.normal(0, max(1.5, expected_demand * 0.18))
            daily_qty = max(0, int(round(expected_demand + demand_noise)))

            # Deduce inventory
            simulated_inv = max(0, simulated_inv - daily_qty)
            # Occasional replenishment simulation in history
            if simulated_inv < p["lead_time"] * p["base_daily"]:
                simulated_inv += int(p["base_daily"] * p["lead_time"] * 2.5)

            # Revenue
            revenue = round(daily_qty * p["price"], 2)

            records.append({
                "date": curr_date.strftime("%Y-%m-%d"),
                "product_id": p["id"],
                "product_name": p["name"],
                "category": p["category"],
                "quantity_sold": daily_qty,
                "unit_price": p["price"],
                "revenue": revenue,
                "inventory_level": simulated_inv if day_idx < num_days - 1 else p["inventory_level"],
                "lead_time_days": p["lead_time"]
            })

            curr_date += timedelta(days=1)

    df = pd.DataFrame(records)
    df.to_csv(CSV_FILE, index=False)
    print(f"Generated {len(df)} historical sales records -> {CSV_FILE}")
    return df

if __name__ == "__main__":
    generate_historical_sales_dataset()
