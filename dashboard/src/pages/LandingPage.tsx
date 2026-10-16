import React from "react";
import {
  Sparkles,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  Zap,
  BarChart3,
  Cpu,
  Layers,
  CheckCircle,
} from "lucide-react";
import { DemandIntelligenceWorld } from "../components/DemandIntelligenceWorld";

interface LandingPageProps {
  onEnterDashboard: () => void;
  onOpenForecasting: () => void;
  onLogin: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onEnterDashboard, onOpenForecasting, onLogin }) => {
  return (
    <div className="min-h-screen bg-[#F6F8FC] text-slate-900 flex flex-col selection:bg-blue-600 selection:text-white">
      {/* Top Navbar */}
      <header className="h-20 border-b border-slate-200/80 bg-white/70 backdrop-blur-md px-6 lg:px-16 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/25 text-white font-black text-base tracking-tighter">
            DQ
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-base tracking-tight text-slate-900">DEMANDIQ</span>
              <span className="px-1.5 py-0.5 text-[11px] font-extrabold bg-blue-100 text-blue-700 rounded-md">
                AI
              </span>
            </div>
            <p className="text-[10px] text-slate-500 font-medium">Demand Forecasting & Inventory Optimization</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={onOpenForecasting}
            className="hidden sm:inline-flex text-xs font-bold text-slate-600 hover:text-slate-900 transition-colors"
          >
            View Forecast Engine
          </button>
          <button onClick={onLogin} className="btn-primary">
            <span>Sign In</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative px-6 lg:px-16 pt-12 pb-16 overflow-hidden">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Hero Copy */}
          <div className="lg:col-span-6 space-y-6 z-10">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200/90 text-blue-700 text-xs font-extrabold tracking-wide">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Next-Gen Enterprise Demand Intelligence</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-slate-900 tracking-tight leading-[1.08]">
              Know What Your Business Will{" "}
              <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 bg-clip-text text-transparent">
                Need Next.
              </span>
            </h1>

            <p className="text-base sm:text-lg text-slate-600 font-normal leading-relaxed max-w-xl">
              DemandIQ AI transforms historical sales and inventory data into accurate demand forecasts, probabilistic
              safety buffers, and actionable replenishment decisions.
            </p>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button onClick={onLogin} className="btn-primary text-sm px-6 py-3.5">
                <span>Sign In to Continue</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <button onClick={onOpenForecasting} className="btn-secondary text-sm px-5 py-3.5">
                <span>View Forecast Engine</span>
              </button>
            </div>

            {/* Quick Metrics Bar */}
            <div className="pt-6 grid grid-cols-3 gap-4 border-t border-slate-200/80">
              <div>
                <p className="text-2xl font-black text-slate-900">16.5%</p>
                <p className="text-xs font-semibold text-slate-600">Model WAPE Accuracy</p>
              </div>
              <div>
                <p className="text-2xl font-black text-blue-600">95.0%</p>
                <p className="text-xs font-semibold text-slate-600">Service Level Buffer</p>
              </div>
              <div>
                <p className="text-2xl font-black text-emerald-600">0%</p>
                <p className="text-xs font-semibold text-slate-600">Data Leakage Rate</p>
              </div>
            </div>
          </div>

          {/* Right 3D Visual Metaphor */}
          <div className="lg:col-span-6 h-[460px] lg:h-[540px] relative">
            <div className="w-full h-full glass-panel overflow-hidden border border-slate-200 shadow-2xl relative">
              <DemandIntelligenceWorld interactive={true} />

              <div className="absolute top-4 left-4 bg-white/80 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-200 text-[11px] font-bold text-slate-700 shadow-xs">
                Demand Intelligence World (Interactive 3D)
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Decision Workflow Grid */}
      <section className="px-6 lg:px-16 py-16 bg-white border-y border-slate-200/80">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center space-y-2 max-w-2xl mx-auto">
            <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              From Raw Transactions to Exact Purchase Orders
            </h2>
            <p className="text-sm text-slate-500 font-medium">
              Every prediction connects mathematically to a real-world inventory decision.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="p-6 rounded-2xl bg-[#F6F8FC] border border-slate-200 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
                1
              </div>
              <h3 className="font-extrabold text-sm text-slate-900">Leakage-Free ML</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Automated calendar, lag, and past-only rolling features trained across Naive, Linear, Random Forest, and XGBoost.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-[#F6F8FC] border border-slate-200 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold">
                2
              </div>
              <h3 className="font-extrabold text-sm text-slate-900">Multi-Horizon Curves</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Dynamic 7, 14, 30, 60, and 90-day recursive forecasts with expanding confidence bands.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-[#F6F8FC] border border-slate-200 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                3
              </div>
              <h3 className="font-extrabold text-sm text-slate-900">Optimization Math</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Precise Lead-Time Demand, Safety Stock (Z × σ × √L), and Reorder Points (ROP).
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-[#F6F8FC] border border-slate-200 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-100 text-cyan-700 flex items-center justify-center font-bold">
                4
              </div>
              <h3 className="font-extrabold text-sm text-slate-900">Actionable Orders</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Automated REORDER_NOW, REORDER_SOON, MONITOR, and OVERSTOCK decisions with full explainability text.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto py-8 px-6 lg:px-16 border-t border-slate-200 bg-white flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500">
        <p>© 2026 DemandIQ AI. Enterprise Demand & Inventory Optimization System.</p>
        <div className="flex gap-4 mt-2 sm:mt-0 font-medium">
          <button onClick={onLogin} className="hover:text-blue-600">
            Sign In
          </button>
          <span>•</span>
          <a href="/docs" target="_blank" className="hover:text-blue-600">
            REST API Docs
          </a>
        </div>
      </footer>
    </div>
  );
};
