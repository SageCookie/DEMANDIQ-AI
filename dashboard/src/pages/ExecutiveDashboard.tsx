import React, { useState } from "react";
import {
  Boxes,
  AlertTriangle,
  TrendingUp,
  PackageCheck,
  Percent,
  Clock,
  ArrowUpRight,
  Filter,
  Search,
  ChevronRight,
  AlertOctagon,
  CheckCircle2,
  Info,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import { DashboardSummary, InventoryRecommendation } from "../types";

interface ExecutiveDashboardProps {
  summary: DashboardSummary | null;
  loading: boolean;
  onSelectProduct: (productId: string) => void;
  onNavigateToForecast: (productId: string) => void;
}

export const ExecutiveDashboard: React.FC<ExecutiveDashboardProps> = ({
  summary,
  loading,
  onSelectProduct,
  onNavigateToForecast,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [selectedRisk, setSelectedRisk] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  if (loading || !summary) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-28 bg-white/70 rounded-2xl border border-slate-200" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 h-80 bg-white/70 rounded-2xl border border-slate-200" />
          <div className="lg:col-span-4 h-80 bg-white/70 rounded-2xl border border-slate-200" />
        </div>
      </div>
    );
  }

  const { kpis, recommendations, category_summary, model_performance, recent_forecast_runs } = summary;

  // Filter recommendations
  const filteredRecs = recommendations.filter((r) => {
    const matchCat = selectedCategory === "ALL" || r.category === selectedCategory;
    const matchRisk = selectedRisk === "ALL" || r.stockout_risk === selectedRisk;
    const matchSearch =
      r.product_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.product_id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCat && matchRisk && matchSearch;
  });

  const categories = Array.from(new Set(recommendations.map((r) => r.category)));

  return (
    <div className="space-y-6">
      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Total Products */}
        <div className="card p-4 space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider">Total Products</span>
            <Boxes className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-2xl font-black text-slate-900">{kpis.total_products}</p>
          <p className="text-[10px] text-slate-600 font-medium">100% telemetry synced</p>
        </div>

        {/* Products to Reorder */}
        <div className="card p-4 space-y-2 border-l-4 border-l-blue-600">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider">Needs Reorder</span>
            <PackageCheck className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-2xl font-black text-blue-600">{kpis.products_requiring_reorder}</p>
          <p className="text-[10px] text-blue-700 font-semibold">Immediate / Soon action</p>
        </div>

        {/* High Stockout Risk */}
        <div className="card p-4 space-y-2 border-l-4 border-l-rose-500">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider">Stockout Risk</span>
            <AlertTriangle className="w-4 h-4 text-rose-600" />
          </div>
          <p className="text-2xl font-black text-rose-600">{kpis.high_stockout_risk}</p>
          <p className="text-[10px] text-rose-700 font-semibold">Breaching safety stock</p>
        </div>

        {/* Overstocked */}
        <div className="card p-4 space-y-2 border-l-4 border-l-purple-500">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider">Overstocked</span>
            <AlertOctagon className="w-4 h-4 text-purple-600" />
          </div>
          <p className="text-2xl font-black text-purple-600">{kpis.overstocked_products}</p>
          <p className="text-[10px] text-purple-700 font-semibold">Surplus capital tie-up</p>
        </div>

        {/* Average Forecast Error */}
        <div className="card p-4 space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider">Forecast Error</span>
            <Percent className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-2xl font-black text-slate-900">{kpis.average_forecast_error}</p>
          <p className="text-[10px] text-emerald-700 font-semibold">Champion Model Test Error</p>
        </div>

        {/* Average Coverage */}
        <div className="card p-4 space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider">Avg Coverage</span>
            <Clock className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="text-2xl font-black text-slate-900">{kpis.average_inventory_coverage}</p>
          <p className="text-[10px] text-slate-600 font-medium">Safe operational runway</p>
        </div>
      </div>

      {/* Analytics Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Demand & Forecast Breakdown by Category */}
        <div className="lg:col-span-8 card p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-extrabold text-slate-900">Demand & Inventory Position by Category</h3>
              <p className="text-xs text-slate-500">30-day forecasted unit demand vs currently available inventory</p>
            </div>
            <span className="badge-blue self-start sm:self-auto font-mono text-[11px]">
              {category_summary.length} Categories Active
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={category_summary} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="category" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(255, 255, 255, 0.95)",
                    borderRadius: "0.75rem",
                    border: "1px solid #e2e8f0",
                    boxShadow: "0 10px 25px -5px rgba(0,0,0,0.05)",
                    fontSize: "12px",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                <Bar dataKey="forecast_demand" name="30d Demand Forecast" fill="#2563eb" radius={[6, 6, 0, 0]} />
                <Bar dataKey="current_inventory" name="Current Available Stock" fill="#635bff" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Model Performance Snapshot */}
        <div className="lg:col-span-4 card p-6 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-extrabold text-slate-900">Production ML Model</h3>
              <span className="badge-green font-mono text-[10px]">ACTIVE</span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{model_performance.model_name}</p>
          </div>

          <div className="space-y-3 py-2 border-y border-slate-100">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Model Version:</span>
              <span className="font-mono font-bold text-slate-900">{model_performance.model_version}</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Test WAPE Error:</span>
              <span className="font-bold text-emerald-600">{model_performance.test_metrics?.WAPE}%</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Mean Absolute Error (MAE):</span>
              <span className="font-bold text-slate-900">{model_performance.test_metrics?.MAE} units</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Root Mean Sq Error (RMSE):</span>
              <span className="font-bold text-slate-900">{model_performance.test_metrics?.RMSE}</span>
            </div>
          </div>

          <div className="p-3 bg-blue-50/60 border border-blue-200/70 rounded-xl text-xs text-blue-900 flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <p className="text-[11px] leading-tight">
              Model selected via rigorous holdout cross-validation against Naive, Moving Average, and XGBoost baselines.
            </p>
          </div>
        </div>
      </div>

      {/* Interactive Recommendations & Decision Table */}
      <div className="card p-6 space-y-4">
        {/* Filters Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">Inventory Optimization & Reorder Decisions</h3>
            <p className="text-xs text-slate-500">
              Click any SKU row to inspect safety stock math, lead-time demand, and AI reasoning.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Search */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search SKU or name..."
                className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-800"
              />
            </div>

            {/* Category Filter */}
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl font-medium text-slate-700"
            >
              <option value="ALL">All Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>

            {/* Risk Filter */}
            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl font-medium text-slate-700"
            >
              <option value="ALL">All Risk Levels</option>
              <option value="CRITICAL">Critical Risk</option>
              <option value="HIGH">High Risk</option>
              <option value="MEDIUM">Medium Risk</option>
              <option value="LOW">Low Risk</option>
            </select>
          </div>
        </div>

        {/* Recommendations Table */}
        <div className="overflow-x-auto border border-slate-200/80 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-600 font-bold uppercase tracking-wider text-[10px] border-b border-slate-200/80">
              <tr>
                <th className="py-3 px-4">SKU / Product</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Current Stock</th>
                <th className="py-3 px-4">30d Demand</th>
                <th className="py-3 px-4">Reorder Point (ROP)</th>
                <th className="py-3 px-4">Coverage</th>
                <th className="py-3 px-4">Stockout Risk</th>
                <th className="py-3 px-4">Recommendation</th>
                <th className="py-3 px-4">Order Qty</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-800">
              {filteredRecs.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-400">
                    No products matching your search filter.
                  </td>
                </tr>
              ) : (
                filteredRecs.map((rec) => (
                  <tr
                    key={rec.product_id}
                    onClick={() => onSelectProduct(rec.product_id)}
                    className="hover:bg-blue-50/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{rec.product_name}</div>
                      <div className="text-[10px] font-mono text-slate-600">{rec.product_id}</div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">{rec.category}</td>
                    <td className="py-3.5 px-4 font-bold text-slate-900">{rec.current_inventory} units</td>
                    <td className="py-3.5 px-4 text-blue-600 font-bold">{rec.forecast_demand} units</td>
                    <td className="py-3.5 px-4 font-mono text-slate-700">{rec.reorder_point} units</td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`font-semibold ${
                          rec.inventory_coverage_days < rec.lead_time_days
                            ? "text-rose-600"
                            : rec.inventory_coverage_days > 60
                            ? "text-purple-600"
                            : "text-slate-700"
                        }`}
                      >
                        {rec.inventory_coverage_days}d
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {rec.stockout_risk === "CRITICAL" ? (
                        <span className="badge-critical">CRITICAL</span>
                      ) : rec.stockout_risk === "HIGH" ? (
                        <span className="badge-high">HIGH</span>
                      ) : rec.stockout_risk === "MEDIUM" ? (
                        <span className="badge-medium">MEDIUM</span>
                      ) : (
                        <span className="badge-low">LOW</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      {rec.recommendation === "REORDER_NOW" ? (
                        <span className="badge-critical font-bold">REORDER NOW</span>
                      ) : rec.recommendation === "REORDER_SOON" ? (
                        <span className="badge-high font-bold">REORDER SOON</span>
                      ) : rec.recommendation === "OVERSTOCK" ? (
                        <span className="badge-purple font-bold">OVERSTOCK</span>
                      ) : (
                        <span className="badge-low font-bold">{rec.recommendation}</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                      {rec.recommended_order_quantity > 0 ? (
                        <span className="text-blue-600 font-black">+{rec.recommended_order_quantity}</span>
                      ) : (
                        <span className="text-slate-600 font-bold">0</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onNavigateToForecast(rec.product_id);
                        }}
                        className="p-1 rounded-lg hover:bg-white text-slate-400 hover:text-blue-600 transition-colors"
                        title="View Forecast Curve"
                      >
                        <ArrowUpRight className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
