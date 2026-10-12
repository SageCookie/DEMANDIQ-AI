import React, { useState } from "react";
import {
  Boxes,
  Shield,
  Clock,
  ArrowRight,
  TrendingUp,
  Sliders,
  Sparkles,
  Info,
  CheckCircle2,
} from "lucide-react";
import { InventoryRecommendation, Product } from "../types";

interface InventoryOptimizationPageProps {
  recommendations: InventoryRecommendation[];
  products: Product[];
  onSelectProduct: (productId: string) => void;
}

export const InventoryOptimizationPage: React.FC<InventoryOptimizationPageProps> = ({
  recommendations,
  products,
  onSelectProduct,
}) => {
  // What-If Simulator State
  const [simProductCode, setSimProductCode] = useState<string>(products[0]?.product_code || "P001");
  const [simServiceLevel, setSimServiceLevel] = useState<number>(0.95);
  const [simLeadTime, setSimLeadTime] = useState<number>(7);
  const [simCurrentStock, setSimCurrentStock] = useState<number>(80);

  const selectedSimRec = recommendations.find((r) => r.product_id === simProductCode) || recommendations[0];

  // Simulator Math
  const zScoreMap: Record<number, number> = {
    0.90: 1.282,
    0.95: 1.645,
    0.98: 2.054,
    0.99: 2.326,
  };
  const zFactor = zScoreMap[simServiceLevel] || 1.645;
  const avgDailyDemand = selectedSimRec?.average_daily_demand || 20.0;
  const sigma = avgDailyDemand * 0.28;

  const simLTD = Math.round(avgDailyDemand * simLeadTime);
  const simSS = Math.round(zFactor * sigma * Math.sqrt(simLeadTime));
  const simROP = simLTD + simSS;
  const simTarget = Math.round(avgDailyDemand * 30 + simSS);
  const simROQ = Math.max(0, simTarget - simCurrentStock);

  return (
    <div className="space-y-6">
      {/* Mathematical Principles Header */}
      <div className="card p-6 bg-gradient-to-r from-blue-50/60 via-indigo-50/40 to-white space-y-4">
        <div>
          <h2 className="text-base font-extrabold text-slate-900">Inventory Optimization Engine</h2>
          <p className="text-xs text-slate-600 mt-0.5">
            Statistical inventory decision formulas powering automated reorder points and purchase orders.
          </p>
        </div>

        {/* Formula Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2">
          <div className="p-3.5 bg-white rounded-xl border border-slate-200/90 space-y-1 shadow-xs">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Lead-Time Demand</p>
            <p className="text-sm font-mono font-black text-slate-900">LTD = ADD × L</p>
            <p className="text-[11px] text-slate-500 leading-tight">Average daily demand multiplied by supplier lead time.</p>
          </div>

          <div className="p-3.5 bg-white rounded-xl border border-slate-200/90 space-y-1 shadow-xs">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Safety Stock Buffer</p>
            <p className="text-sm font-mono font-black text-blue-600">SS = Z × σ × √L</p>
            <p className="text-[11px] text-slate-500 leading-tight">Service-level buffer protecting against demand variance.</p>
          </div>

          <div className="p-3.5 bg-white rounded-xl border border-slate-200/90 space-y-1 shadow-xs">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Reorder Point (ROP)</p>
            <p className="text-sm font-mono font-black text-indigo-600">ROP = LTD + SS</p>
            <p className="text-[11px] text-slate-500 leading-tight">Threshold where a purchase replenishment must be triggered.</p>
          </div>

          <div className="p-3.5 bg-white rounded-xl border border-slate-200/90 space-y-1 shadow-xs">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Recommended Order</p>
            <p className="text-sm font-mono font-black text-emerald-600">ROQ = Target - Stock - OnOrder</p>
            <p className="text-[11px] text-slate-500 leading-tight">Clamped to zero to prevent unintentional surplus capital tie-up.</p>
          </div>
        </div>
      </div>

      {/* Interactive "What-If" Scenario Simulator */}
      <div className="card p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-slate-900">Interactive "What-If" Parameter Simulator</h3>
              <p className="text-xs text-slate-500">
                Dynamically adjust supplier lead time and service levels to see real-time impact on stock thresholds.
              </p>
            </div>
          </div>
          <span className="badge-blue font-mono text-[11px]">Real-time Calculation</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Controls */}
          <div className="lg:col-span-6 space-y-4">
            {/* SKU selection */}
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Target Product</label>
              <select
                value={simProductCode}
                onChange={(e) => {
                  setSimProductCode(e.target.value);
                  const p = products.find((pr) => pr.product_code === e.target.value);
                  if (p) {
                    setSimLeadTime(p.lead_time_days);
                    setSimCurrentStock(p.current_inventory);
                  }
                }}
                className="w-full px-3 py-2 text-xs font-bold bg-slate-50 border border-slate-200 rounded-xl text-slate-900"
              >
                {products.map((p) => (
                  <option key={p.product_code} value={p.product_code}>
                    {p.product_code} - {p.product_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Service Level Slider */}
            <div>
              <div className="flex justify-between text-xs font-bold text-slate-700 mb-1">
                <span>Target Service Level (Z-Factor)</span>
                <span className="text-blue-600 font-mono">{(simServiceLevel * 100).toFixed(0)}% (Z={zFactor})</span>
              </div>
              <div className="grid grid-cols-4 gap-2">
                {[0.90, 0.95, 0.98, 0.99].map((lvl) => (
                  <button
                    key={lvl}
                    onClick={() => setSimServiceLevel(lvl)}
                    className={`py-1.5 text-xs font-bold rounded-lg border transition-all ${
                      simServiceLevel === lvl
                        ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                        : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    {(lvl * 100).toFixed(0)}%
                  </button>
                ))}
              </div>
            </div>

            {/* Lead Time Slider */}
            <div>
              <div className="flex justify-between text-xs font-bold text-slate-700 mb-1">
                <span>Supplier Lead Time (Days)</span>
                <span className="font-mono text-slate-900">{simLeadTime} days</span>
              </div>
              <input
                type="range"
                min="2"
                max="30"
                value={simLeadTime}
                onChange={(e) => setSimLeadTime(Number(e.target.value))}
                className="w-full accent-blue-600"
              />
            </div>

            {/* Current Stock Slider */}
            <div>
              <div className="flex justify-between text-xs font-bold text-slate-700 mb-1">
                <span>Current Available Stock</span>
                <span className="font-mono text-slate-900">{simCurrentStock} units</span>
              </div>
              <input
                type="range"
                min="0"
                max="500"
                value={simCurrentStock}
                onChange={(e) => setSimCurrentStock(Number(e.target.value))}
                className="w-full accent-blue-600"
              />
            </div>
          </div>

          {/* Real-time Math Output Card */}
          <div className="lg:col-span-6 p-6 rounded-2xl bg-[#F6F8FC] border border-slate-200/90 space-y-4">
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-500">
              Live Optimization Outcome
            </h4>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-white rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 font-bold uppercase">Lead-Time Demand</span>
                <p className="text-xl font-black text-slate-900 mt-0.5">{simLTD} units</p>
              </div>
              <div className="p-3 bg-white rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 font-bold uppercase">Safety Buffer</span>
                <p className="text-xl font-black text-blue-600 mt-0.5">{simSS} units</p>
              </div>
              <div className="p-3 bg-white rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 font-bold uppercase">Reorder Point (ROP)</span>
                <p className="text-xl font-black text-indigo-600 mt-0.5">{simROP} units</p>
              </div>
              <div className="p-3 bg-white rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 font-bold uppercase">Target Stock (30d)</span>
                <p className="text-xl font-black text-slate-900 mt-0.5">{simTarget} units</p>
              </div>
            </div>

            <div
              className={`p-4 rounded-xl border ${
                simCurrentStock <= simROP
                  ? "bg-rose-50 border-rose-200 text-rose-900"
                  : "bg-emerald-50 border-emerald-200 text-emerald-900"
              }`}
            >
              <div className="flex justify-between items-center">
                <span className="text-xs font-black uppercase tracking-wider">
                  {simCurrentStock <= simROP ? "REPLENISHMENT TRIGGERED" : "INVENTORY OPTIMAL"}
                </span>
                <span className="text-xs font-mono font-bold">
                  Recommended Order: <span className="text-base font-black">+{simROQ}</span> units
                </span>
              </div>
              <p className="text-xs mt-1 leading-relaxed">
                {simCurrentStock <= simROP
                  ? `Current inventory (${simCurrentStock} units) has breached the reorder point (${simROP} units). An order of ${simROQ} units restores stock to target.`
                  : `Current inventory (${simCurrentStock} units) is safely above the reorder point (${simROP} units). No action required today.`}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Complete Recommendations Table */}
      <div className="card p-6 space-y-4">
        <h3 className="text-sm font-extrabold text-slate-900">Active Inventory Optimization Roster</h3>
        <div className="overflow-x-auto border border-slate-200/80 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-600 font-bold uppercase tracking-wider text-[10px] border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">SKU / Product</th>
                <th className="py-3 px-4">Lead Time</th>
                <th className="py-3 px-4">Daily Demand</th>
                <th className="py-3 px-4">Lead-Time Demand</th>
                <th className="py-3 px-4">Safety Stock</th>
                <th className="py-3 px-4">Reorder Point</th>
                <th className="py-3 px-4">Current Stock</th>
                <th className="py-3 px-4">Recommendation</th>
                <th className="py-3 px-4 font-mono">Order Qty</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-800">
              {recommendations.map((r) => (
                <tr
                  key={r.product_id}
                  onClick={() => onSelectProduct(r.product_id)}
                  className="hover:bg-blue-50/30 cursor-pointer transition-colors"
                >
                  <td className="py-3.5 px-4 font-bold text-slate-900">{r.product_name}</td>
                  <td className="py-3.5 px-4 text-slate-600">{r.lead_time_days} days</td>
                  <td className="py-3.5 px-4 font-mono">{r.average_daily_demand}/d</td>
                  <td className="py-3.5 px-4 font-mono font-bold text-slate-900">{r.lead_time_demand}</td>
                  <td className="py-3.5 px-4 font-mono text-blue-600 font-bold">{r.safety_stock}</td>
                  <td className="py-3.5 px-4 font-mono font-bold text-indigo-600">{r.reorder_point}</td>
                  <td className="py-3.5 px-4 font-bold text-slate-900">{r.current_inventory}</td>
                  <td className="py-3.5 px-4">
                    {r.recommendation === "REORDER_NOW" ? (
                      <span className="badge-critical font-bold">REORDER NOW</span>
                    ) : r.recommendation === "REORDER_SOON" ? (
                      <span className="badge-high font-bold">REORDER SOON</span>
                    ) : r.recommendation === "OVERSTOCK" ? (
                      <span className="badge-purple font-bold">OVERSTOCK</span>
                    ) : (
                      <span className="badge-low font-bold">{r.recommendation}</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 font-mono font-bold text-blue-600">
                    {r.recommended_order_quantity > 0 ? `+${r.recommended_order_quantity}` : "0"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
