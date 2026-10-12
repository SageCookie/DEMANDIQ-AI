import React, { useState, useEffect } from "react";
import { Cpu, RefreshCw, CheckCircle2, Award, Zap, Clock, ShieldCheck, Play } from "lucide-react";
import { api } from "../lib/api";

export const ModelRegistryPage: React.FC = () => {
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [training, setTraining] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<any | null>(null);

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

  const handleRetrain = async () => {
    setTraining(true);
    try {
      const res = await api.triggerTrain();
      alert(`Model retraining completed! New champion model: ${res.champion_model} (${res.model_version})`);
      fetchModels();
    } catch (err: any) {
      alert(err.message || "Retraining failed");
    } finally {
      setTraining(false);
    }
  };

  const handlePromote = async (version: string) => {
    try {
      await api.promoteModel(version);
      alert(`Model version ${version} promoted to PRODUCTION.`);
      fetchModels();
    } catch (err: any) {
      alert(err.message || "Promotion failed");
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
          <button onClick={handleRetrain} disabled={training} className="btn-primary">
            <Play className={`w-3.5 h-3.5 ${training ? "animate-spin" : ""}`} />
            <span>{training ? "Training ML Pipeline..." : "Retrain Pipeline"}</span>
          </button>
        </div>
      </div>

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
                    {m.status !== "PRODUCTION" ? (
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
