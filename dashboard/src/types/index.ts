export interface Product {
  id: number;
  product_code: string;
  product_name: string;
  category: string;
  unit_price: number;
  lead_time_days: number;
  active: boolean;
  current_inventory: number;
  on_order_quantity: number;
  created_at: string;
}

export interface ForecastItem {
  product_id: string;
  forecast_date: string;
  predicted_demand: number;
  lower_bound: number;
  upper_bound: number;
  model_version: string;
  generated_at: string;
}

export interface HistoricalSale {
  date: string;
  actual_demand: number;
  revenue: number;
}

export interface ForecastResponse {
  product_id: string;
  product_name: string;
  category: string;
  horizon_days: number;
  model_version: string;
  generated_at: string;
  forecasts: ForecastItem[];
  historical_sales: HistoricalSale[];
}

export interface InventoryRecommendation {
  product_id: string;
  product_name: string;
  category: string;
  current_inventory: number;
  forecast_demand: number;
  average_daily_demand: number;
  lead_time_days: number;
  lead_time_demand: number;
  safety_stock: number;
  reorder_point: number;
  inventory_coverage_days: number;
  recommended_order_quantity: number;
  stockout_risk: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  overstock_status: "OVERSTOCKED" | "HEALTHY";
  recommendation: "REORDER_NOW" | "REORDER_SOON" | "MONITOR" | "NO_ACTION" | "OVERSTOCK";
  explanation?: string;
}

export interface DashboardSummary {
  kpis: {
    total_products: number;
    products_requiring_reorder: number;
    high_stockout_risk: number;
    overstocked_products: number;
    average_forecast_error: string;
    average_inventory_coverage: string;
  };
  recommendations: InventoryRecommendation[];
  risk_breakdown: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  category_summary: {
    category: string;
    products: number;
    forecast_demand: number;
    current_inventory: number;
  }[];
  model_performance: {
    model_name: string;
    model_version: string;
    training_date?: string;
    test_metrics: {
      MAE: number;
      RMSE: number;
      MAPE: number;
      WAPE: number;
      sMAPE?: number;
    };
    all_model_comparisons?: {
      model_name: string;
      MAE: number;
      RMSE: number;
      MAPE: number;
      WAPE: number;
      training_time_ms: number;
    }[];
  };
  recent_forecast_runs: {
    id: number;
    model_name: string;
    model_version: string;
    MAE: number;
    RMSE: number;
    MAPE: number;
    WAPE: number;
    status: string;
    timestamp: string;
  }[];
}

export interface SystemStatus {
  api_status: string;
  database_status: string;
  model_status: string;
  production_model: string;
  production_version: string;
  last_training_run: string | null;
  last_forecast_generation: string | null;
  data_freshness_date: string | null;
  system_version: string;
  environment: string;
}

export interface DataQualityReport {
  validation_report: {
    total_records: number;
    missing_dates: number;
    missing_product_ids: number;
    negative_quantities: number;
    negative_prices: number;
    negative_inventory: number;
    duplicate_records: number;
    invalid_dates: number;
    missing_columns: string[];
    warnings: string[];
    data_coverage_start: string;
    data_coverage_end: string;
    product_count: number;
    health_score: number;
  };
  cleaning_audit: {
    rows_before: number;
    rows_after: number;
    duplicates_removed: number;
    missing_imputed: number;
    dates_corrected: number;
    zero_days_filled: number;
    logs: string[];
  };
  total_records: number;
  health_score: number;
  status: string;
}

export type UserRole =
  | "ADMIN"
  | "DATA_SCIENTIST"
  | "INVENTORY_MANAGER"
  | "ANALYST"
  | "OPERATIONS_MANAGER"
  | "VIEWER";

export interface User {
  id: string;
  username: string;
  name: string;
  role: UserRole;
  token: string;
  organization_id: number;
  organization_name: string;
}
