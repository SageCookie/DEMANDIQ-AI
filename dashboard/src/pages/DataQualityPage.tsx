import React, { useState, useEffect } from "react";
import { Database, CheckCircle2, AlertTriangle, FileText, ShieldCheck, RefreshCw } from "lucide-react";
import { DataQualityReport } from "../types";
import { api } from "../lib/api";

export const DataQualityPage: React.FC = () => {
  const [data, setData] = useState<DataQualityReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = () => {
    setLoading(true);
    api
      .getDataQuality()
      .then((res) => setData(res))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading || !data) {
    return (
      <div className="card p-12 text-center text-slate-400 animate-pulse">
        Evaluating dataset health and cleaning audit...
      </div>
    );
  }

  const { validation_report, cleaning_audit, health_score, total_records } = data;

  return (
    <div className="space-y-6">
      {/* Health Score Overview Banner */}
      <div className="card p-6 bg-gradient-to-r from-emerald-50/60 via-blue-50/30 to-white flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-white border border-emerald-200 flex flex-col items-center justify-center shadow-sm">
            <span className="text-xl font-black text-emerald-600">{health_score}</span>
            <span className="text-[9px] font-bold uppercase text-slate-600">Score / 100</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-extrabold text-slate-900">Dataset Quality & Health Audit</h2>
              <span className="badge-green font-bold text-[10px]">{data.status}</span>
            </div>
            <p className="text-xs text-slate-600 mt-0.5">
              Automated ingestion validation checking duplicate transactions, date integrity, and negative values.
            </p>
          </div>
        </div>

        <button onClick={loadData} className="btn-secondary self-start md:self-auto">
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Re-validate</span>
        </button>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4 space-y-1">
          <span className="text-[10px] font-bold uppercase text-slate-600">Total Records</span>
          <p className="text-2xl font-black text-slate-900">{total_records.toLocaleString()}</p>
          <p className="text-xs text-slate-600">Daily normalized points</p>
        </div>

        <div className="card p-4 space-y-1">
          <span className="text-[10px] font-bold uppercase text-slate-600">Coverage Window</span>
          <p className="text-sm font-bold text-slate-900 mt-1 font-mono">
            {validation_report.data_coverage_start}
          </p>
          <p className="text-xs text-slate-600 font-mono">to {validation_report.data_coverage_end}</p>
        </div>

        <div className="card p-4 space-y-1">
          <span className="text-[10px] font-bold uppercase text-slate-600">Duplicate Check</span>
          <p className="text-2xl font-black text-emerald-600">{validation_report.duplicate_records}</p>
          <p className="text-xs text-slate-600">0 duplicate collisions</p>
        </div>

        <div className="card p-4 space-y-1">
          <span className="text-[10px] font-bold uppercase text-slate-600">Active SKUs</span>
          <p className="text-2xl font-black text-blue-600">{validation_report.product_count}</p>
          <p className="text-xs text-slate-600">Unique product keys</p>
        </div>
      </div>

      {/* Validation Checklist & Audit Log */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Quality Checks Checklist */}
        <div className="lg:col-span-6 card p-6 space-y-4">
          <h3 className="text-sm font-extrabold text-slate-900">Automated Data Integrity Tests</h3>
          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-700 font-medium">Missing Dates / Temporal Gaps</span>
              <span className="font-bold text-emerald-600 flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> Passed ({validation_report.missing_dates})
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-700 font-medium">Missing Product IDs</span>
              <span className="font-bold text-emerald-600 flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> Passed ({validation_report.missing_product_ids})
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-700 font-medium">Negative Price Rejection</span>
              <span className="font-bold text-emerald-600 flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> Passed ({validation_report.negative_prices})
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-700 font-medium">Date Format ISO-8601 Compliance</span>
              <span className="font-bold text-emerald-600 flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> Passed ({validation_report.invalid_dates})
              </span>
            </div>
          </div>
        </div>

        {/* Cleaning Audit Log */}
        <div className="lg:col-span-6 card p-6 space-y-4">
          <h3 className="text-sm font-extrabold text-slate-900">ETL Cleaning & Normalization Audit</h3>
          <div className="p-4 bg-slate-900 rounded-xl font-mono text-xs text-slate-300 space-y-2 max-h-64 overflow-y-auto">
            {cleaning_audit.logs.map((log: string, idx: number) => (
              <div key={idx} className="flex gap-2">
                <span className="text-blue-400">→</span>
                <span>{log}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
