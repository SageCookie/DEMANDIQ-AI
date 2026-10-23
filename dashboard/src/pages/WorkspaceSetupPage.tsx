import React, { useEffect, useState } from "react";
import { Database, FileUp, Loader2, Sparkles, CheckCircle2, ArrowRight } from "lucide-react";
import { api } from "../lib/api";
import { UserRole } from "../types";

interface WorkspaceSetupPageProps {
  currentRole: UserRole;
  onImportData: () => void;
  onReady: () => void;
}

export const WorkspaceSetupPage: React.FC<WorkspaceSetupPageProps> = ({ currentRole, onImportData, onReady }) => {
  const [starting, setStarting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const canSetUp = ["ADMIN", "DATA_SCIENTIST"].includes(currentRole);

  useEffect(() => {
    if (!jobId) return;
    const interval = window.setInterval(async () => {
      try {
        const job = await api.getTrainingJob(jobId);
        setMessage(job.message);
        if (job.status === "SUCCEEDED") {
          window.clearInterval(interval);
          onReady();
        }
        if (job.status === "FAILED") {
          window.clearInterval(interval);
          setMessage(job.error_message || "The setup training job did not finish. Check Model Registry for details.");
        }
      } catch {
        // A free hosted API can take a moment to wake; keep polling quietly.
      }
    }, 2500);
    return () => window.clearInterval(interval);
  }, [jobId, onReady]);

  const startDemo = async () => {
    setStarting(true);
    setMessage(null);
    try {
      const result = await api.useDemoData();
      setJobId(result.training_job?.id || null);
      setMessage(result.message);
    } catch (err: any) {
      setMessage(err.message || "Unable to start the demo workspace.");
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 py-4">
      <div className="card p-8 bg-gradient-to-br from-blue-600 via-indigo-600 to-cyan-600 text-white overflow-hidden relative">
        <Sparkles className="absolute -right-6 -top-6 w-40 h-40 opacity-15" />
        <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-blue-100">New workspace</p>
        <h2 className="mt-2 text-3xl font-black tracking-tight">Turn sales history into decisions.</h2>
        <p className="mt-3 max-w-2xl text-sm text-blue-50 leading-relaxed">
          Start with your own sales export, or explore the full product with a safe demo dataset. DemandIQ will create your catalog, sync inventory, train the model, and prepare reorder recommendations.
        </p>
      </div>

      {!canSetUp ? (
        <div className="card p-6 border border-amber-200 bg-amber-50 text-sm text-amber-900">
          Your account can view a prepared workspace, but an Administrator or Data Scientist must import the first dataset.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-5">
          <div className="card p-6 space-y-4 border-2 border-blue-100">
            <div className="w-11 h-11 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center"><FileUp className="w-5 h-5" /></div>
            <div>
              <h3 className="font-extrabold text-slate-900">Import your sales CSV</h3>
              <p className="mt-1 text-xs text-slate-600 leading-relaxed">Recommended. Upload historical sales with product IDs, dates, quantities, and prices. Common headings are mapped automatically.</p>
            </div>
            <div className="space-y-1 text-xs text-slate-600">
              <p><CheckCircle2 className="inline w-3.5 h-3.5 text-emerald-600 mr-1" />Preview and validate before replacing data</p>
              <p><CheckCircle2 className="inline w-3.5 h-3.5 text-emerald-600 mr-1" />Catalog and inventory created automatically</p>
              <p><CheckCircle2 className="inline w-3.5 h-3.5 text-emerald-600 mr-1" />Forecasts and reorder actions prepared automatically</p>
            </div>
            <button onClick={onImportData} className="btn-primary w-full justify-center"><span>Import my data</span><ArrowRight className="w-4 h-4" /></button>
          </div>

          <div className="card p-6 space-y-4">
            <div className="w-11 h-11 rounded-xl bg-violet-100 text-violet-700 flex items-center justify-center"><Database className="w-5 h-5" /></div>
            <div>
              <h3 className="font-extrabold text-slate-900">Explore with demo data</h3>
              <p className="mt-1 text-xs text-slate-600 leading-relaxed">Load the included sample catalog and year of sales history. You can replace it with your CSV later.</p>
            </div>
            <p className="text-xs text-slate-600 rounded-xl bg-slate-50 p-3 border border-slate-100">Best for a first look at forecasts, safety stock, and purchase recommendations.</p>
            <button onClick={startDemo} disabled={starting || Boolean(jobId)} className="btn-secondary w-full justify-center disabled:opacity-50">
              {starting || jobId ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              <span>{jobId ? "Preparing workspace..." : "Use demo data"}</span>
            </button>
          </div>
        </div>
      )}

      {message && <div role="status" className="card p-4 text-sm text-slate-700 border border-blue-100 bg-blue-50">{message}</div>}

      <p className="text-center text-xs text-slate-500">This is a shared operational workspace. Public self-sign-up is intentionally not enabled because accounts share the same business data.</p>
    </div>
  );
};
