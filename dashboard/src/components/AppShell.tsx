import React, { useState } from "react";
import {
  LayoutDashboard,
  TrendingUp,
  Boxes,
  AlertTriangle,
  Package,
  History,
  Cpu,
  Database,
  Activity,
  Settings,
  ChevronDown,
  RefreshCw,
  Bell,
  Sparkles,
  ExternalLink,
  Menu,
  X,
  UserCheck,
  ShieldAlert,
} from "lucide-react";
import { UserRole } from "../types";

export type NavTab =
  | "dashboard"
  | "forecasting"
  | "inventory"
  | "risk"
  | "products"
  | "history"
  | "models"
  | "data-quality"
  | "system-health"
  | "settings";

interface AppShellProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  currentRole: UserRole;
  onRefresh: () => void;
  isRefreshing: boolean;
  onOpenLanding: () => void;
  onLogout?: () => void;
  userName?: string;
  organizationName?: string;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  activeTab,
  onTabChange,
  currentRole,
  onRefresh,
  isRefreshing,
  onOpenLanding,
  onLogout,
  userName,
  organizationName,
  children,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);

  const navItems = [
    { id: "dashboard" as NavTab, label: "Dashboard", icon: LayoutDashboard },
    { id: "forecasting" as NavTab, label: "Demand Forecast", icon: TrendingUp },
    { id: "inventory" as NavTab, label: "Inventory Optimization", icon: Boxes },
    { id: "risk" as NavTab, label: "Risk Monitoring", icon: AlertTriangle },
    { id: "products" as NavTab, label: "Products Catalog", icon: Package },
    { id: "history" as NavTab, label: "Forecast History", icon: History },
    { id: "models" as NavTab, label: "Model Registry", icon: Cpu },
    { id: "data-quality" as NavTab, label: "Data Quality", icon: Database },
    { id: "system-health" as NavTab, label: "System Health", icon: Activity },
    { id: "settings" as NavTab, label: "Settings", icon: Settings },
  ];

  const roles: { role: UserRole; name: string; title: string }[] = [
    { role: "ADMIN", name: "Administrator", title: "Full System Access" },
    { role: "DATA_SCIENTIST", name: "Dr. Elena Vance", title: "ML & Feature Pipelines" },
    { role: "INVENTORY_MANAGER", name: "Marcus Chen", title: "Stock & Reorder Actions" },
    { role: "ANALYST", name: "Sarah Jenkins", title: "Forecasting & Metrics" },
    { role: "OPERATIONS_MANAGER", name: "David Miller", title: "Supply Chain & POs" },
    { role: "VIEWER", name: "Guest Viewer", title: "Read-Only Auditor" },
  ];

  const activeRoleData = roles.find((r) => r.role === currentRole) || roles[0];

  return (
    <div className="flex h-screen w-full bg-[#F6F8FC] overflow-hidden">
      {/* Sidebar (Desktop) */}
      <aside className="hidden lg:flex flex-col w-64 bg-white/90 backdrop-blur-xl border-r border-slate-200/90 shadow-sm z-30">
        {/* Brand Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-500 flex items-center justify-center shadow-md shadow-blue-500/20 text-white font-black text-sm tracking-tighter">
              DQ
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-sm tracking-tight text-slate-900">DEMANDIQ</span>
                <span className="px-1.5 py-0.2 text-[10px] font-extrabold bg-blue-100 text-blue-700 rounded-md">
                  AI
                </span>
              </div>
              <p className="text-[10px] text-slate-500 font-medium">Demand & Stock Intelligence</p>
            </div>
          </div>
        </div>

        {organizationName && (
          <div className="mx-4 mt-3 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2">
            <p className="text-[9px] font-bold uppercase tracking-wider text-blue-600">Workspace</p>
            <p className="mt-0.5 truncate text-xs font-bold text-blue-950" title={organizationName}>{organizationName}</p>
          </div>
        )}

        {/* Navigation Menu */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <div className="px-3 pb-1 text-[10px] font-bold tracking-wider text-slate-600 uppercase">
            Intelligence Modules
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? "bg-blue-600 text-white shadow-sm shadow-blue-500/25"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/70"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-600"}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Showcase Hero Link */}
        <div className="p-3 border-t border-slate-100">
          <button
            onClick={onOpenLanding}
            className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl bg-gradient-to-r from-blue-50 via-indigo-50/50 to-cyan-50/40 border border-blue-200/60 text-blue-800 text-xs font-bold hover:shadow-sm transition-all"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              <span>3D Hero Experience</span>
            </div>
            <ExternalLink className="w-3 h-3 text-blue-500" />
          </button>
        </div>

        {/* Authenticated User Profile + Logout */}
        <div className="p-3 border-t border-slate-100 relative">
          <div className="flex items-center gap-2.5 p-2 rounded-xl bg-slate-50/70 border border-slate-100">
            <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-xs shadow-sm shadow-blue-500/20">
              {currentRole?.charAt(0) || "U"}
            </div>
            <div className="overflow-hidden flex-1 min-w-0">
              <p className="text-xs font-bold text-slate-900 truncate">{userName || currentRole || "User"}</p>
              <p className="text-[10px] text-blue-600 font-semibold truncate">{currentRole || "VIEWER"}</p>
            </div>
          </div>
          {onLogout && (
            <button
              onClick={onLogout}
              className="mt-2 w-full text-xs font-bold text-rose-600 hover:text-rose-700 hover:bg-rose-50 rounded-lg py-2 border border-rose-200/60 transition-colors text-center"
            >
              Sign Out
            </button>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white/80 backdrop-blur-md border-b border-slate-200/80 px-4 lg:px-8 flex items-center justify-between shrink-0 z-20">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-sm lg:text-base font-extrabold text-slate-900 tracking-tight capitalize">
                {activeTab.replace("-", " ")}
              </h1>
              <p className="text-[11px] text-slate-500 font-medium hidden sm:block">
                Predict Demand. Optimize Inventory. Decide Smarter.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Live System Pill */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-emerald-50 border border-emerald-200/80 rounded-full">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[11px] font-bold text-emerald-700">API & ML Model Operational</span>
            </div>

            {/* Refresh Button */}
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 transition-all shadow-sm"
              title="Refresh telemetry"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-blue-600" : ""}`} />
            </button>

            {/* Landing Hero Action */}
            <button
              onClick={onOpenLanding}
              className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-blue-700 bg-blue-50 border border-blue-200/80 hover:bg-blue-100/70 rounded-xl transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Hero Mode</span>
            </button>
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 lg:hidden flex">
            <div className="w-64 bg-white h-full p-4 flex flex-col justify-between shadow-2xl animate-in slide-in-from-left duration-200">
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-blue-600 text-white font-black text-xs flex items-center justify-center">
                      DQ
                    </div>
                    <span className="font-extrabold text-sm text-slate-900">DEMANDIQ AI</span>
                  </div>
                  <button onClick={() => setMobileMenuOpen(false)} className="p-1 rounded-lg text-slate-500">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <nav className="mt-4 space-y-1">
                  {navItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = activeTab === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          onTabChange(item.id);
                          setMobileMenuOpen(false);
                        }}
                        className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold ${
                          isActive ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100"
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                        <span>{item.label}</span>
                      </button>
                    );
                  })}
                </nav>
              </div>
            </div>
            <div className="flex-1" onClick={() => setMobileMenuOpen(false)} />
          </div>
        )}

        {/* Screen View Container */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-8 space-y-6">{children}</main>
      </div>
    </div>
  );
};
