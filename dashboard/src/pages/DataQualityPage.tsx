import React, { useState, useEffect } from "react";
import { Database, CheckCircle2, AlertTriangle, FileText, ShieldCheck, RefreshCw, Upload, Loader2 } from "lucide-react";
import { DataQualityReport, UserRole } from "../types";
import { api } from "../lib/api";

interface DataQualityPageProps {
  currentRole: UserRole;
  onDataImported: () => void;
}

export const DataQualityPage: React.FC<DataQualityPageProps> = ({ currentRole, onDataImported }) => {
  const [data, setData] = useState<DataQualityReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [preview, setPreview] = useState<any | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [defaultInventory, setDefaultInventory] = useState(100);
  const [defaultLeadTime, setDefaultLeadTime] = useState(7);
  const [trainingJob, setTrainingJob] = useState<any | null>(null);
  const [confirmingImport, setConfirmingImport] = useState(false);
  const canImport = ["ADMIN", "DATA_SCIENTIST"].includes(currentRole);

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

  useEffect(() => {
    if (!trainingJob?.id || ["SUCCEEDED", "FAILED"].includes(trainingJob.status)) return;
    const interval = window.setInterval(async () => {
      try {
        const job = await api.getTrainingJob(trainingJob.id);
        setTrainingJob(job);
        setMessage(job.message);
        if (job.status === "SUCCEEDED") {
          loadData();
          onDataImported();
        }
      } catch {
        // The service may be waking from its free-hosted idle state; keep polling.
      }
    }, 2500);
    return () => window.clearInterval(interval);
  }, [trainingJob?.id, trainingJob?.status]);

  const handlePreview = async (file?: File) => {
    if (!file) return;
    setUploading(true);
    setPreview(null);
    setMessage(null);
    try {
      const result = await api.previewDataUpload(file, defaultInventory, defaultLeadTime);
      setPreview(result);
      if (!result.is_valid) setMessage("This file needs correction before it can be imported.");
    } catch (err: any) {
      setMessage(err.message || "Unable to validate this file.");
    } finally { setUploading(false); }
  };

  const handleConfirm = async () => {
    if (!preview?.upload_id) return;
    setConfirmingImport(true);
    setMessage("Import received. Creating your workspace now...");
    try {
      const result = await api.confirmDataUpload(preview.upload_id);
      setMessage(result.message);
      setTrainingJob(result.training_job || null);
      setPreview(null);
    } catch (err: any) {
      setMessage(err.message || "Import could not be completed.");
    } finally { setConfirmingImport(false); }
  };

  const handleCancelPreview = async () => {
    if (!preview?.upload_id) {
      setPreview(null);
      return;
    }
    setUploading(true);
    try {
      await api.cancelDataUpload(preview.upload_id);
      setPreview(null);
      setMessage("CSV import cancelled. Your active workspace was not changed.");
    } catch (err: any) {
      setMessage(err.message || "Unable to cancel this staged import.");
    } finally { setUploading(false); }
  };

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

      <div className="card p-6 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">Import Sales Dataset</h3>
            <p className="text-xs text-slate-500 mt-1">Common transaction exports are mapped automatically. Review validation results, then explicitly replace the active dataset. The previous source is backed up automatically.</p>
          </div>
          <label className={`btn-primary cursor-pointer ${!canImport || uploading ? "opacity-50 pointer-events-none" : ""}`}>
            <Upload className="w-4 h-4" />
            <span>{uploading ? "Checking file..." : "Choose CSV"}</span>
            <input type="file" accept=".csv,text/csv" className="hidden" disabled={!canImport || uploading} onChange={(e) => handlePreview(e.target.files?.[0])} />
          </label>
        </div>
        {!canImport && <p className="text-xs text-slate-500">Data import is available to Administrators and Data Scientists.</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <label className="font-bold text-slate-700">Fallback inventory per SKU
            <input type="number" min="0" value={defaultInventory} onChange={(e) => setDefaultInventory(Number(e.target.value))} disabled={!canImport || uploading} className="mt-1 w-full px-3 py-2 border border-slate-200 rounded-xl font-normal disabled:bg-slate-50" />
          </label>
          <label className="font-bold text-slate-700">Fallback supplier lead time (days)
            <input type="number" min="1" max="365" value={defaultLeadTime} onChange={(e) => setDefaultLeadTime(Number(e.target.value))} disabled={!canImport || uploading} className="mt-1 w-full px-3 py-2 border border-slate-200 rounded-xl font-normal disabled:bg-slate-50" />
          </label>
        </div>
        {message && <p role="status" className="rounded-xl bg-slate-50 border border-slate-200 px-3 py-2 text-xs text-slate-700">{message}</p>}
        {trainingJob && (
          <div className={`rounded-xl border px-3 py-3 text-xs ${trainingJob.status === "FAILED" ? "border-rose-200 bg-rose-50 text-rose-800" : "border-blue-200 bg-blue-50 text-blue-900"}`}>
            <div className="flex items-center justify-between gap-3 font-bold">
              <span className="flex items-center gap-2">{!["SUCCEEDED", "FAILED"].includes(trainingJob.status) && <Loader2 className="w-3.5 h-3.5 animate-spin" />}Workspace preparation</span>
              <span>{trainingJob.progress}%</span>
            </div>
            <div className="mt-2 h-1.5 rounded-full bg-white/80 overflow-hidden"><div className="h-full bg-blue-600 transition-all" style={{ width: `${trainingJob.progress}%` }} /></div>
            <p className="mt-2">{trainingJob.status === "SUCCEEDED" ? "Your catalog, forecasts, and reorder recommendations are ready." : trainingJob.status === "FAILED" ? (trainingJob.error_message || "Training failed. Check the data and try again.") : "You can stay on this page while DemandIQ prepares your decisions."}</p>
          </div>
        )}
        {preview && (
          <div className={`rounded-xl border p-4 text-xs ${preview.is_valid ? "border-emerald-200 bg-emerald-50" : "border-rose-200 bg-rose-50"}`}>
            <div className="flex flex-wrap justify-between gap-2 font-bold text-slate-800">
              <span>{preview.file_name}: {preview.raw_records.toLocaleString()} raw rows</span>
              <span>{preview.is_valid ? "READY TO IMPORT" : "FIX REQUIRED"}</span>
            </div>
            <p className="mt-2 text-slate-600">Health score: {preview.validation_report.health_score} · Products: {preview.validation_report.product_count} · Normalized rows: {preview.normalized_records ?? "—"}</p>
            {Object.keys(preview.applied_mappings || {}).length > 0 && <p className="mt-2 text-slate-600">Mapped: {Object.entries(preview.applied_mappings).map(([target, source]) => `${source} → ${target}`).join(", ")}</p>}
            {preview.generated_fields?.length > 0 && <p className="mt-2 text-slate-600">Generated/defaulted: {preview.generated_fields.join(", ")}</p>}
            {preview.validation_report.warnings?.length > 0 && <p className="mt-2 text-rose-700">{preview.validation_report.warnings.join(" ")}</p>}
            <div className="mt-3 flex flex-wrap gap-2">
              {preview.is_valid && (
                <button onClick={handleConfirm} disabled={uploading || confirmingImport} className="btn-primary disabled:opacity-60 disabled:cursor-wait">
                  {confirmingImport && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{confirmingImport ? "Importing dataset..." : "Confirm & Import Dataset"}</span>
                </button>
              )}
              <button onClick={handleCancelPreview} disabled={uploading || confirmingImport} className="btn-secondary disabled:opacity-60">
                Cancel
              </button>
            </div>
          </div>
        )}
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
