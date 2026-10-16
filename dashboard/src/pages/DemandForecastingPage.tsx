import React, { useState, useEffect } from "react";
import {
  TrendingUp,
  Calendar,
  Layers,
  ArrowRight,
  Download,
  Info,
  Clock,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Product, ForecastResponse, UserRole } from "../types";
import { api } from "../lib/api";

interface DemandForecastingPageProps {
  products: Product[];
  initialProductId?: string;
  currentRole: UserRole;
}

export const DemandForecastingPage: React.FC<DemandForecastingPageProps> = ({
  products,
  initialProductId,
  currentRole,
}) => {
  const [selectedProductId, setSelectedProductId] = useState<string>(
    initialProductId || products[0]?.product_code || "P001"
  );
  const [horizonDays, setHorizonDays] = useState<number>(30);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const canGenerateForecast = ["ADMIN", "DATA_SCIENTIST", "ANALYST"].includes(currentRole);

  useEffect(() => {
    if (initialProductId) {
      setSelectedProductId(initialProductId);
    }
  }, [initialProductId]);

  const loadForecast = async () => {
    if (!selectedProductId || !canGenerateForecast) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.generateForecast(selectedProductId, horizonDays);
      setForecastData(data);
    } catch (err: any) {
      setError(err.message || "Failed to generate forecast.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (canGenerateForecast) loadForecast();
  }, [selectedProductId, horizonDays, canGenerateForecast]);

  // Combine historical and forecasted series for charts
  const chartData = React.useMemo(() => {
    if (!forecastData) return [];
    const combined: any[] = [];

    // Historical sales
    forecastData.historical_sales.forEach((h) => {
      combined.push({
        date: h.date,
        actual_demand: h.actual_demand,
        predicted_demand: null,
        lower_bound: null,
        upper_bound: null,
      });
    });

    // Future forecast items
    forecastData.forecasts.forEach((f) => {
      combined.push({
        date: f.forecast_date,
        actual_demand: null,
        predicted_demand: f.predicted_demand,
        lower_bound: f.lower_bound,
        upper_bound: f.upper_bound,
      });
    });

    return combined;
  }, [forecastData]);

  // Export CSV function
  const handleExportCSV = () => {
    if (!forecastData) return;
    const headers = "date,actual_demand,predicted_demand,lower_bound,upper_bound,model_version\n";
    const rows = forecastData.forecasts
      .map(
        (f) =>
          `${f.forecast_date},,${f.predicted_demand},${f.lower_bound},${f.upper_bound},${f.model_version}`
      )
      .join("\n");

    const blob = new Blob([headers + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `demand_forecast_${selectedProductId}_${horizonDays}d.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const selectedProduct = products.find((p) => p.product_code === selectedProductId);

  return (
    <div className="space-y-6">
      {/* Control Bar */}
      <div className="card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Product Selector */}
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
              Select Product SKU
            </label>
            <select
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
              className="px-3.5 py-2 text-xs font-bold bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 text-slate-900"
            >
              {products.map((p) => (
                <option key={p.product_code} value={p.product_code}>
                  {p.product_code} — {p.product_name}
                </option>
              ))}
            </select>
          </div>

          {/* Horizon Selector */}
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
              Forecast Horizon
            </label>
            <div className="flex rounded-xl bg-slate-100 p-1 border border-slate-200">
              {[7, 14, 30, 60, 90].map((h) => (
                <button
                  key={h}
                  onClick={() => setHorizonDays(h)}
                  className={`px-3 py-1 text-xs font-bold rounded-lg transition-all ${
                    horizonDays === h
                      ? "bg-white text-blue-600 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {h}d
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Actions & Metadata */}
        <div className="flex items-center gap-3 self-end md:self-auto">
          <button onClick={loadForecast} disabled={loading || !canGenerateForecast} title={!canGenerateForecast ? "Your role cannot generate forecasts" : undefined} className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Generate</span>
          </button>
          <button onClick={handleExportCSV} disabled={!forecastData} className="btn-secondary">
            <Download className="w-3.5 h-3.5 text-slate-600" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {!canGenerateForecast && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
          Forecast generation requires an Administrator, Data Scientist, or Analyst account. You can still review saved forecasts in Forecast History.
        </div>
      )}

      {/* Summary Row */}
      {selectedProduct && forecastData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-4 space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Selected Product</p>
            <p className="text-base font-extrabold text-slate-900 truncate">{selectedProduct.product_name}</p>
            <p className="text-xs text-slate-500">{selectedProduct.category}</p>
          </div>
          <div className="card p-4 space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Planning Horizon Demand</p>
            <p className="text-xl font-black text-blue-600">
              {Math.round(forecastData.forecasts.reduce((a, b) => a + b.predicted_demand, 0))} units
            </p>
            <p className="text-xs text-slate-500">
              Avg daily: ~{Math.round(forecastData.forecasts.reduce((a, b) => a + b.predicted_demand, 0) / horizonDays)}/day
            </p>
          </div>
          <div className="card p-4 space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Champion Model</p>
            <p className="text-base font-extrabold text-slate-900 font-mono">{forecastData.model_version}</p>
            <p className="text-xs text-emerald-600 font-semibold">Production Validated</p>
          </div>
          <div className="card p-4 space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Generation Timestamp</p>
            <p className="text-xs font-mono font-bold text-slate-800">{forecastData.generated_at}</p>
            <p className="text-[10px] text-slate-500">95% Prediction Interval</p>
          </div>
        </div>
      )}

      {/* Main Forecast Chart */}
      <div className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">Historical Actuals vs Future Forecast</h3>
            <p className="text-xs text-slate-500">
              Historical actual sales (last 30d) seamlessly stitched with {horizonDays}-day future predictions & confidence bounds.
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-semibold">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-slate-400" />
              <span className="text-slate-600">Historical Actuals</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-1 bg-blue-600 rounded-full" />
              <span className="text-blue-700">Forecast Curve</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 bg-blue-100 rounded-sm border border-blue-300" />
              <span className="text-slate-500">95% Confidence Band</span>
            </div>
          </div>
        </div>

        {error ? (
          <div className="p-8 text-center text-rose-600 font-semibold text-xs border border-rose-200 rounded-2xl bg-rose-50/50">
            {error}
          </div>
        ) : (
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} tickLine={false} />
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
                <Area
                  type="monotone"
                  dataKey="upper_bound"
                  stroke="none"
                  fill="#93c5fd"
                  fillOpacity={0.25}
                  name="Upper Bound (95%)"
                />
                <Area
                  type="monotone"
                  dataKey="lower_bound"
                  stroke="none"
                  fill="#ffffff"
                  fillOpacity={0.9}
                  name="Lower Bound (95%)"
                />
                <Line
                  type="monotone"
                  dataKey="actual_demand"
                  stroke="#64748b"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  name="Actual Historical"
                />
                <Line
                  type="monotone"
                  dataKey="predicted_demand"
                  stroke="#2563eb"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: "#2563eb" }}
                  name="Predicted Demand"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Forecast Data Grid */}
      {forecastData && (
        <div className="card p-6 space-y-4">
          <h3 className="text-sm font-extrabold text-slate-900">
            Day-by-Day Forecast Output ({forecastData.forecasts.length} Days)
          </h3>
          <div className="overflow-x-auto border border-slate-200/80 rounded-xl max-h-96">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 text-slate-600 font-bold uppercase tracking-wider text-[10px] sticky top-0 z-10 border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-4">Date</th>
                  <th className="py-2.5 px-4">Predicted Demand</th>
                  <th className="py-2.5 px-4">Lower Bound (95%)</th>
                  <th className="py-2.5 px-4">Upper Bound (95%)</th>
                  <th className="py-2.5 px-4">Model Version</th>
                  <th className="py-2.5 px-4 text-right">Generated At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium text-slate-800">
                {forecastData.forecasts.map((f, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-4 font-mono font-bold text-slate-900">{f.forecast_date}</td>
                    <td className="py-2.5 px-4 font-bold text-blue-600">{f.predicted_demand} units</td>
                    <td className="py-2.5 px-4 font-mono text-slate-500">{f.lower_bound}</td>
                    <td className="py-2.5 px-4 font-mono text-slate-500">{f.upper_bound}</td>
                    <td className="py-2.5 px-4 font-mono text-xs text-slate-600">{f.model_version}</td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-slate-400 text-right">{f.generated_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
