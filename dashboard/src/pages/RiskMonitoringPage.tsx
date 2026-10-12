import React, { useState } from "react";
import { AlertOctagon, AlertTriangle, ShieldCheck, HelpCircle, CheckCircle, Package } from "lucide-react";
import { InventoryRecommendation } from "../types";

interface RiskMonitoringPageProps {
  recommendations: InventoryRecommendation[];
  onSelectProduct: (productId: string) => void;
}

export const RiskMonitoringPage: React.FC<RiskMonitoringPageProps> = ({
  recommendations,
  onSelectProduct,
}) => {
  const [activeFilter, setActiveFilter] = useState<string>("ALL");

  const criticalItems = recommendations.filter((r) => r.stockout_risk === "CRITICAL");
  const highItems = recommendations.filter((r) => r.stockout_risk === "HIGH");
  const mediumItems = recommendations.filter((r) => r.stockout_risk === "MEDIUM");
  const overstockedItems = recommendations.filter((r) => r.recommendation === "OVERSTOCK");

  const filteredItems = recommendations.filter((r) => {
    if (activeFilter === "CRITICAL") return r.stockout_risk === "CRITICAL";
    if (activeFilter === "HIGH") return r.stockout_risk === "HIGH";
    if (activeFilter === "MEDIUM") return r.stockout_risk === "MEDIUM";
    if (activeFilter === "OVERSTOCK") return r.recommendation === "OVERSTOCK";
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Risk Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <button
          onClick={() => setActiveFilter(activeFilter === "CRITICAL" ? "ALL" : "CRITICAL")}
          className={`card p-5 text-left border-l-4 border-l-rose-500 transition-all ${
            activeFilter === "CRITICAL" ? "ring-2 ring-rose-500 bg-rose-50/20" : ""
          }`}
        >
          <div className="flex items-center justify-between text-rose-600">
            <span className="text-xs font-bold uppercase tracking-wider">Critical Stockout</span>
            <AlertOctagon className="w-5 h-5" />
          </div>
          <p className="text-3xl font-black text-rose-600 mt-2">{criticalItems.length}</p>
          <p className="text-xs text-rose-700/80 mt-1 font-medium">Exhausts before supplier lead time</p>
        </button>

        <button
          onClick={() => setActiveFilter(activeFilter === "HIGH" ? "ALL" : "HIGH")}
          className={`card p-5 text-left border-l-4 border-l-amber-500 transition-all ${
            activeFilter === "HIGH" ? "ring-2 ring-amber-500 bg-amber-50/20" : ""
          }`}
        >
          <div className="flex items-center justify-between text-amber-600">
            <span className="text-xs font-bold uppercase tracking-wider">High Risk</span>
            <AlertTriangle className="w-5 h-5" />
          </div>
          <p className="text-3xl font-black text-amber-600 mt-2">{highItems.length}</p>
          <p className="text-xs text-amber-700/80 mt-1 font-medium">Approaches or breaches safety buffer</p>
        </button>

        <button
          onClick={() => setActiveFilter(activeFilter === "MEDIUM" ? "ALL" : "MEDIUM")}
          className={`card p-5 text-left border-l-4 border-l-yellow-400 transition-all ${
            activeFilter === "MEDIUM" ? "ring-2 ring-yellow-400 bg-yellow-50/20" : ""
          }`}
        >
          <div className="flex items-center justify-between text-yellow-600">
            <span className="text-xs font-bold uppercase tracking-wider">Medium Risk</span>
            <HelpCircle className="w-5 h-5" />
          </div>
          <p className="text-3xl font-black text-yellow-600 mt-2">{mediumItems.length}</p>
          <p className="text-xs text-yellow-700/80 mt-1 font-medium">Below reorder point (order soon)</p>
        </button>

        <button
          onClick={() => setActiveFilter(activeFilter === "OVERSTOCK" ? "ALL" : "OVERSTOCK")}
          className={`card p-5 text-left border-l-4 border-l-purple-500 transition-all ${
            activeFilter === "OVERSTOCK" ? "ring-2 ring-purple-500 bg-purple-50/20" : ""
          }`}
        >
          <div className="flex items-center justify-between text-purple-600">
            <span className="text-xs font-bold uppercase tracking-wider">Overstocked SKUs</span>
            <Package className="w-5 h-5" />
          </div>
          <p className="text-3xl font-black text-purple-600 mt-2">{overstockedItems.length}</p>
          <p className="text-xs text-purple-700/80 mt-1 font-medium">Excess inventory exceeding safety target</p>
        </button>
      </div>

      {/* Explanatory Decision Cards */}
      <div className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">Explainable AI Decision Audit</h3>
            <p className="text-xs text-slate-500">
              Clear mathematical reasons generated for every stockout risk and replenishment trigger.
            </p>
          </div>
          {activeFilter !== "ALL" && (
            <button onClick={() => setActiveFilter("ALL")} className="text-xs font-bold text-blue-600 hover:underline">
              Clear Filter
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredItems.map((item) => (
            <div
              key={item.product_id}
              onClick={() => onSelectProduct(item.product_id)}
              className="p-5 rounded-2xl border border-slate-200/90 bg-white hover:border-slate-300 hover:shadow-md transition-all cursor-pointer space-y-3"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-mono font-bold text-slate-600 uppercase">{item.product_id}</span>
                  <h4 className="font-extrabold text-sm text-slate-900">{item.product_name}</h4>
                  <p className="text-xs text-slate-600">{item.category}</p>
                </div>
                <div>
                  {item.stockout_risk === "CRITICAL" ? (
                    <span className="badge-critical font-bold">CRITICAL</span>
                  ) : item.stockout_risk === "HIGH" ? (
                    <span className="badge-high font-bold">HIGH</span>
                  ) : item.recommendation === "OVERSTOCK" ? (
                    <span className="badge-purple font-bold">OVERSTOCK</span>
                  ) : (
                    <span className="badge-low font-bold">LOW</span>
                  )}
                </div>
              </div>

              {/* Explanatory Reasoning Quote */}
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-700 leading-relaxed font-medium">
                "{item.explanation || "Stock metrics currently within normal operational parameters."}"
              </div>

              {/* Telemetry Footer */}
              <div className="grid grid-cols-3 gap-2 pt-1 text-[11px] border-t border-slate-100">
                <div>
                  <span className="text-slate-600 block">Stock:</span>
                  <span className="font-bold text-slate-900">{item.current_inventory} units</span>
                </div>
                <div>
                  <span className="text-slate-600 block">Reorder Point:</span>
                  <span className="font-bold text-blue-600">{item.reorder_point} units</span>
                </div>
                <div>
                  <span className="text-slate-600 block">Coverage:</span>
                  <span className="font-bold text-slate-900">{item.inventory_coverage_days} days</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
