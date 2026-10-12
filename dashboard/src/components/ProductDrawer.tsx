import React, { useEffect, useState } from "react";
import { X, TrendingUp, Package, Shield, Calendar, ArrowRight, CheckCircle2, AlertOctagon } from "lucide-react";
import { api } from "../lib/api";

interface ProductDrawerProps {
  productId: string | null;
  onClose: () => void;
  onNavigateToForecast: (productId: string) => void;
}

export const ProductDrawer: React.FC<ProductDrawerProps> = ({ productId, onClose, onNavigateToForecast }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!productId) {
      setData(null);
      return;
    }
    setLoading(true);
    api
      .getProductOptimization(productId)
      .then((res) => setData(res))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [productId]);

  if (!productId) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/30 backdrop-blur-xs flex justify-end">
      <div
        className="w-full max-w-lg bg-white h-full shadow-2xl border-l border-slate-200 flex flex-col justify-between animate-in slide-in-from-right duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 font-black">
              {productId}
            </div>
            <div>
              <h3 className="text-base font-extrabold text-slate-900">{data?.product_name || productId}</h3>
              <p className="text-xs text-slate-500 font-medium">{data?.category || "Loading SKU specifications..."}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-400 hover:text-slate-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="space-y-4 animate-pulse">
              <div className="h-24 bg-slate-100 rounded-2xl" />
              <div className="h-36 bg-slate-100 rounded-2xl" />
              <div className="h-48 bg-slate-100 rounded-2xl" />
            </div>
          ) : data ? (
            <>
              {/* Primary Decision Banner */}
              <div
                className={`p-4 rounded-2xl border ${
                  data.stockout_risk === "CRITICAL"
                    ? "bg-rose-50 border-rose-200 text-rose-900"
                    : data.stockout_risk === "HIGH"
                    ? "bg-amber-50 border-amber-200 text-amber-900"
                    : data.recommendation === "OVERSTOCK"
                    ? "bg-purple-50 border-purple-200 text-purple-900"
                    : "bg-emerald-50 border-emerald-200 text-emerald-900"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {data.stockout_risk === "CRITICAL" ? (
                      <AlertOctagon className="w-5 h-5 text-rose-600" />
                    ) : (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    )}
                    <span className="text-xs font-black uppercase tracking-wider">{data.recommendation}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-white/70 shadow-xs">
                    {data.stockout_risk} RISK
                  </span>
                </div>
                <p className="text-xs leading-relaxed font-medium">{data.explanation}</p>
              </div>

              {/* Inventory Position Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 bg-slate-50/70 border border-slate-200/80 rounded-2xl">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-600">Current Stock</p>
                  <p className="text-xl font-black text-slate-900 mt-1">{data.current_inventory} units</p>
                  <p className="text-[11px] text-slate-600 mt-0.5">On Order: {data.quantity_on_order} units</p>
                </div>
                <div className="p-4 bg-slate-50/70 border border-slate-200/80 rounded-2xl">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-600">30d Demand Forecast</p>
                  <p className="text-xl font-black text-blue-600 mt-1">{data.forecast_demand_30d} units</p>
                  <p className="text-[11px] text-slate-600 mt-0.5">Daily: ~{Math.round(data.forecast_demand_30d / 30)}/day</p>
                </div>
              </div>

              {/* Optimization Parameters */}
              <div className="border border-slate-200 rounded-2xl p-4 space-y-3 bg-white">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-700">Inventory Parameters</h4>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Supplier Lead Time:</span>
                    <span className="font-bold text-slate-900">{data.lead_time_days} days</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Lead-Time Demand (LTD):</span>
                    <span className="font-bold text-slate-900">{data.lead_time_demand} units</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Safety Buffer (Z=1.65):</span>
                    <span className="font-bold text-slate-900">{data.safety_stock} units</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Reorder Point (ROP):</span>
                    <span className="font-bold text-blue-600 font-mono">{data.reorder_point} units</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Recommended Order:</span>
                    <span className="font-black text-emerald-600 text-sm font-mono">
                      {data.recommended_order_quantity} units
                    </span>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500 text-center py-10">Product data unavailable.</p>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-6 border-t border-slate-100 bg-slate-50/50 flex gap-3">
          <button
            onClick={() => {
              onClose();
              if (productId) onNavigateToForecast(productId);
            }}
            className="flex-1 btn-primary"
          >
            <TrendingUp className="w-4 h-4" />
            <span>Open Demand Curves</span>
          </button>
          <button onClick={onClose} className="btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
