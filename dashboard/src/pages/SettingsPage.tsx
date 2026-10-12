import React, { useState } from "react";
import { Settings, Shield, Sliders, Database, Save, Check } from "lucide-react";

export const SettingsPage: React.FC = () => {
  const [serviceLevel, setServiceLevel] = useState<number>(0.95);
  const [defaultHorizon, setDefaultHorizon] = useState<number>(30);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="card p-6">
        <h2 className="text-base font-extrabold text-slate-900">Application & Engine Configuration</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Fine-tune probabilistic parameters and inventory calculation targets.
        </p>

        <form onSubmit={handleSave} className="mt-6 space-y-6 text-xs">
          {/* Service Level */}
          <div className="space-y-2">
            <label className="block font-bold text-slate-700">Default Service Level (Z-Factor Protection)</label>
            <p className="text-slate-500 text-[11px]">
              Determines safety stock buffer size. 95% service level corresponds to Z ≈ 1.645 standard deviations.
            </p>
            <select
              value={serviceLevel}
              onChange={(e) => setServiceLevel(Number(e.target.value))}
              className="px-3.5 py-2 border border-slate-200 rounded-xl bg-slate-50 font-bold text-slate-900"
            >
              <option value={0.90}>90% (Z = 1.282) - Lean Inventory</option>
              <option value={0.95}>95% (Z = 1.645) - Recommended Industry Standard</option>
              <option value={0.98}>98% (Z = 2.054) - High Stockout Protection</option>
              <option value={0.99}>99% (Z = 2.326) - Critical Mission Spares</option>
            </select>
          </div>

          {/* Default Horizon */}
          <div className="space-y-2">
            <label className="block font-bold text-slate-700">Default Planning Forecast Horizon</label>
            <p className="text-slate-500 text-[11px]">Default planning window applied on dashboard metrics.</p>
            <select
              value={defaultHorizon}
              onChange={(e) => setDefaultHorizon(Number(e.target.value))}
              className="px-3.5 py-2 border border-slate-200 rounded-xl bg-slate-50 font-bold text-slate-900"
            >
              <option value={7}>7 Days (Weekly Short-Run)</option>
              <option value={14}>14 Days (Bi-Weekly Sprint)</option>
              <option value={30}>30 Days (Standard Monthly Planning)</option>
              <option value={60}>60 Days (Bi-Monthly Horizon)</option>
              <option value={90}>90 Days (Quarterly Outlook)</option>
            </select>
          </div>

          <div className="pt-4 border-t border-slate-100 flex items-center gap-3">
            <button type="submit" className="btn-primary">
              <Save className="w-4 h-4" />
              <span>Save Configuration</span>
            </button>
            {saved && (
              <span className="text-xs text-emerald-600 font-bold flex items-center gap-1">
                <Check className="w-4 h-4" /> Settings updated successfully
              </span>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};
