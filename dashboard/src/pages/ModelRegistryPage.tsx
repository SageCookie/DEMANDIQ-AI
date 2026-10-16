import React, { useState, useEffect } from "react";
import { Cpu, RefreshCw, CheckCircle2, Award, Zap, Clock, ShieldCheck, Play } from "lucide-react";
import { api } from "../lib/api";
import { UserRole } from "../types";

interface ModelRegistryPageProps {
  currentRole: UserRole;
}

export const ModelRegistryPage: React.FC<ModelRegistryPageProps> = ({ currentRole }) => {
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [training, setTraining] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<any | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<any | null>(null);
  const canTrain = ["ADMIN", "DATA_SCIENTIST"].includes(currentRole);
  const canPromote = currentRole === "DATA_SCIENTIST";

  const fetchModels = async () => {
    setLoading(true);
    try {
      const data = await api.getModels();
      setModels(data);
      if (data.length > 0) setSelectedModel(data[0]);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  useEffect(() => {
    if (!activeJob || ["SUCCEEDED", "FAILED"].includes(activeJob.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const job = await api.getTrainingJob(activeJob.id);
        setActiveJob(job);
        if (job.status === "SUCCEEDED") {
          setActionMessage(`Training completed. Champion model: ${job.model_version}.`);
          fetchModels();
        } else if (job.status === "FAILED") {
          setActionMessage(job.error_message || "Training failed. Review the dataset and retry.");
        }
      } catch (err: any) {
        setActionMessage(err.message || "Unable to retrieve training-job status.");
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [activeJob?.id, activeJob?.status]);

  const handleRetrain = async () => {
    if (!canTrain) return;
    setTraining(true);
    try {
      const job = await api.triggerTrain();
      setActiveJob(job);
      setActionMessage("Training queued. You can keep using the dashboard while the model is evaluated.");
    } catch (err: any) {
      setActionMessage(err.message || "Retraining failed.");
    } finally {
      setTraining(false);
    }
  };

  const handlePromote = async (version: string) => {
    if (!canPromote) return;
    try {
      await api.promoteModel(version);
      setActionMessage(`Model version ${version} is now serving production traffic.`);
      fetchModels();
    } catch (err: any) {
      setActionMessage(err.message || "Promotion failed.");
    }
  };

  const currentProd = models.find((m) => m.status === "PRODUCTION") || models[0];
  const comparisons = currentProd?.all_model_comparisons || [];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-extrabold text-slate-900">Model Registry & Performance Hub</h2>
            <span className="badge-green font-mono text-[10px]">Active Champion: {currentProd?.model_name}</span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Compare cross-validation metrics across baselines and machine learning algorithms without data leakage.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={fetchModels} disabled={loading} className="btn-secondary">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
          <button onClick={handleRetrain} disabled={training || !canTrain || Boolean(activeJob && !["SUCCEEDED", "FAILED"].includes(activeJob.status))} title={!canTrain ? "Your role cannot retrain models" : undefined} className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed">
            <Play className={`w-3.5 h-3.5 ${training ? "animate-spin" : ""}`} />
            <span>{training ? "Queueing Training..." : activeJob && !["SUCCEEDED", "FAILED"].includes(activeJob.status) ? "Training in Background" : "Retrain Pipeline"}</span>
          </button>
        </div>
      </div>

      {!canTrain && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
          Model retraining is available to Administrators and Data Scientists. Promotion is limited to Data Scientists.
        </div>
      )}
      {actionMessage && <div role="status" className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">{actionMessage}</div>}
      {activeJob && !["SUCCEEDED", "FAILED"].includes(activeJob.status) && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3">
          <div className="flex items-center justify-between text-xs font-bold text-blue-900"><span>{activeJob.message}</span><span>{activeJob.progress}%</span></div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-blue-100"><div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${activeJob.progress}%` }} /></div>
        </div>
      )}

      {/* Model Benchmark Comparison Table */}
      <div className="card p-6 space-y-4">
        <div>
          <h3 className="text-sm font-extrabold text-slate-900">Algorithm Benchmark Comparison (Validation Set)</h3>
          <p className="text-xs text-slate-500">
            Real measured validation holdout performance. The model with lowest WAPE & MAE is automatically designated champion.
          </p>
        </div>

        <div className="overflow-x-auto border border-slate-200/80 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-600 font-bold uppercase tracking-wider text-[10px] border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Model Candidate</th>
                <th className="py-3 px-4">WAPE Error (%)</th>
                <th className="py-3 px-4">MAE (Units)</th>
                <th className="py-3 px-4">RMSE</th>
                <th className="py-3 px-4">sMAPE (%)</th>
                <th className="py-3 px-4">Training Time</th>
                <th className="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-800">
              {comparisons.map((c: any, idx: number) => {
                const isChampion = c.model_name === currentProd?.model_name;
                return (
                  <tr key={idx} className={isChampion ? "bg-blue-50/40 font-bold" : "hover:bg-slate-50/50"}>
                    <td className="py-3 px-4 flex items-center gap-2">
                      {isChampion && <Award className="w-4 h-4 text-blue-600 shrink-0" />}
                      <span>{c.model_name}</span>
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">
                      <span className={isChampion ? "text-blue-600" : ""}>{c.WAPE}%</span>
                    </td>
                    <td className="py-3 px-4 font-mono">{c.MAE}</td>
                    <td className="py-3 px-4 font-mono">{c.RMSE}</td>
                    <td className="py-3 px-4 font-mono">{c.sMAPE || c.MAPE}%</td>
                    <td className="py-3 px-4 font-mono text-slate-500">{c.training_time_ms} ms</td>
                    <td className="py-3 px-4 text-right">
                      {isChampion ? (
                        <span className="badge-green text-[10px]">PRODUCTION</span>
                      ) : (
                        <span className="badge-blue text-[10px]">VALIDATED</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Version Registry History */}
      <div className="card p-6 space-y-4">
        <h3 className="text-sm font-extrabold text-slate-900">Model Artifact Versions</h3>
        <div className="overflow-x-auto border border-slate-200/80 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-600 font-bold uppercase tracking-wider text-[10px] border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Version</th>
                <th className="py-3 px-4">Model Name</th>
                <th className="py-3 px-4">Holdout WAPE</th>
                <th className="py-3 px-4">Holdout MAE</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4 text-right">Lifecycle Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-800">
              {models.map((m: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-50/50">
                  <td className="py-3 px-4 font-mono font-bold text-slate-900">{m.model_version}</td>
                  <td className="py-3 px-4 font-bold text-slate-800">{m.model_name}</td>
                  <td className="py-3 px-4 font-mono text-emerald-600 font-bold">{m.WAPE || m.test_metrics?.WAPE}%</td>
                  <td className="py-3 px-4 font-mono">{m.MAE || m.test_metrics?.MAE}</td>
                  <td className="py-3 px-4">
                    {m.status === "PRODUCTION" ? (
                      <span className="badge-green">PRODUCTION</span>
                    ) : (
                      <span className="badge-blue">{m.status || "EXPERIMENT"}</span>
                    )}
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-slate-500">{m.timestamp || m.training_date}</td>
                  <td className="py-3 px-4 text-right">
                    {m.status !== "PRODUCTION" && canPromote ? (
                      <button
                        onClick={() => handlePromote(m.model_version)}
                        className="btn-secondary text-[10px] py-1 px-2.5"
                      >
                        Promote
                      </button>
                    ) : (
                      <span className="text-[11px] text-emerald-600 font-bold">Serving Traffic</span>
                    )}
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
