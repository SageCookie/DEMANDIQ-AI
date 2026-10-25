import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AppShell, NavTab } from "./components/AppShell";
import { LandingPage } from "./pages/LandingPage";
import { ExecutiveDashboard } from "./pages/ExecutiveDashboard";
import { DemandForecastingPage } from "./pages/DemandForecastingPage";
import { InventoryOptimizationPage } from "./pages/InventoryOptimizationPage";
import { RiskMonitoringPage } from "./pages/RiskMonitoringPage";
import { ProductsPage } from "./pages/ProductsPage";
import { ForecastHistoryPage } from "./pages/ForecastHistoryPage";
import { ModelRegistryPage } from "./pages/ModelRegistryPage";
import { DataQualityPage } from "./pages/DataQualityPage";
import { SystemHealthPage } from "./pages/SystemHealthPage";
import { SettingsPage } from "./pages/SettingsPage";
import { WorkspaceSetupPage } from "./pages/WorkspaceSetupPage";
import { ProductDrawer } from "./components/ProductDrawer";
import { DashboardSummary, Product, User, UserRole } from "./types";
import { LoginPage } from "./components/LoginPage";
import { api, getStoredToken, clearStoredToken, onUnauthorized } from "./lib/api";

export function App() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authStatus, setAuthStatus] = useState<"checking" | "authenticated" | "unauthenticated" | "error">("checking");
  const [authError, setAuthError] = useState<string | null>(null);
  const [showLanding, setShowLanding] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");
  const [currentRole, setCurrentRole] = useState<UserRole>("VIEWER");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [dataError, setDataError] = useState<string | null>(null);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [forecastTargetProduct, setForecastTargetProduct] = useState<string>("P001");

  // Register session-expiry / 401 handler (once) to avoid redirect loops / duplicate notifications
  useEffect(() => {
    const handle401 = () => {
      clearStoredToken();
      setCurrentUser(null);
      setCurrentRole("VIEWER");
      setAuthStatus("unauthenticated");
    };
    onUnauthorized(handle401);
    return () => { onUnauthorized(null); };
  }, []);
  useEffect(() => {
    let cancelled = false;

    async function checkSession() {
      const token = getStoredToken();
      if (!token) {
        if (!cancelled) {
          setAuthStatus("unauthenticated");
          setCurrentUser(null);
          setCurrentRole("VIEWER");
        }
        return;
      }

      try {
        const user = await api.getCurrentUser();
        if (!cancelled) {
          setCurrentUser(user);
          setCurrentRole(user.role);
          setAuthStatus("authenticated");
          setAuthError(null);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : String(err);
        const is401 = msg.includes("401") || msg.toLowerCase().includes("unauthorized") || msg.toLowerCase().includes("invalid");
        if (is401) {
          clearStoredToken();
          setCurrentUser(null);
          setCurrentRole("VIEWER");
          setAuthStatus("unauthenticated");
          setAuthError(null);
        } else {
          // Recoverable network/server error: do not discard token permanently, show retry
          setAuthStatus("error");
          setAuthError("Unable to verify session. The server may be unavailable.");
        }
      }
    }

    checkSession();
    return () => { cancelled = true; };
  }, []);

  const handleLoginSuccess = (user: User, token: string) => {
    setCurrentUser(user);
    setCurrentRole(user.role);
    setAuthStatus("authenticated");
    setAuthError(null);
    setShowLanding(false);
    navigate("/dashboard", { replace: true });
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // Local sign-out still protects this browser if the service is offline.
    } finally {
      clearStoredToken();
      setCurrentUser(null);
      setCurrentRole("VIEWER");
      setAuthStatus("unauthenticated");
      setAuthError(null);
      setShowLanding(true);
      navigate("/", { replace: true });
    }
  };

  const handleRetrySession = () => {
    setAuthStatus("checking");
    setAuthError(null);
    (async () => {
      const token = getStoredToken();
      if (!token) {
        setAuthStatus("unauthenticated");
        return;
      }
      try {
        const user = await api.getCurrentUser();
        setCurrentUser(user);
        setCurrentRole(user.role);
        setAuthStatus("authenticated");
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        const is401 = msg.includes("401") || msg.toLowerCase().includes("unauthorized");
        if (is401) {
          clearStoredToken();
          setCurrentUser(null);
          setCurrentRole("VIEWER");
          setAuthStatus("unauthenticated");
        } else {
          setAuthStatus("error");
          setAuthError("Still unable to verify session. Try again or sign in.");
        }
      }
    })();
  };

  const loadData = async () => {
    setIsRefreshing(true);
    try {
      const [sumRes, prodRes] = await Promise.all([
        api.getDashboardSummary(),
        api.getProducts(),
      ]);
      setSummary(sumRes);
      setProducts(prodRes);
      setDataError(null);
    } catch (err: unknown) {
      console.error("Error fetching data:", err);
      setDataError("We could not load the latest demand data. Check that the API is running, then try again.");
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleLoginClick = () => navigate("/login");
  const handleNavigateToForecast = (productId: string) => {
    setForecastTargetProduct(productId);
    setActiveTab("forecasting");
    setSelectedProductId(null);
  };

  // Auth gating: don't render dashboard until session state is resolved
  const isLoginRoute = window.location.pathname === "/login" || window.location.pathname === "/login/";
  const isRootRoute = window.location.pathname === "/" || window.location.pathname === "";

  if (authStatus === "checking") {
    return (
      <div className="min-h-screen bg-[#F6F8FC] flex items-center justify-center text-slate-900">
        <div className="flex flex-col items-center gap-3 text-sm font-medium text-slate-500">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <span>Verifying session...</span>
        </div>
      </div>
    );
  }

  if (authStatus === "unauthenticated" && !showLanding && isLoginRoute) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} onCancel={() => navigate("/", { replace: true })} />;
  }
  if (authStatus === "unauthenticated" && (isRootRoute || showLanding)) {
    return (
      <LandingPage
        onLogin={handleLoginClick}
        onEnterDashboard={() => setShowLanding(false)}
        onOpenForecasting={() => { setShowLanding(false); setActiveTab("forecasting"); }}
      />
    );
  }
  if ((authStatus === "unauthenticated" || authStatus === "error") && isLoginRoute) {
    return (
      <LoginPage
        onLoginSuccess={handleLoginSuccess}
        onCancel={authStatus === "error" ? () => {
          setAuthStatus("unauthenticated");
          setAuthError(null);
          navigate("/", { replace: true });
        } : undefined}
      />
    );
  }

  if (showLanding) {
    return (
      <LandingPage
        onLogin={handleLoginClick}
        onEnterDashboard={() => setShowLanding(false)}
        onOpenForecasting={() => {
          setShowLanding(false);
          setActiveTab("forecasting");
        }}
      />
    );
  }

  return (
    <AppShell
      activeTab={activeTab}
      onTabChange={setActiveTab}
      currentRole={currentUser ? currentUser.role : "VIEWER"}
      onRefresh={loadData}
      isRefreshing={isRefreshing}
      onOpenLanding={() => setShowLanding(true)}
      onLogout={handleLogout}
      userName={currentUser ? (currentUser.name || currentUser.username) : undefined}
      organizationName={currentUser?.organization_name}
    >
      {dataError && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 flex items-center justify-between gap-4 text-sm text-amber-900">
          <span>{dataError}</span>
          <button onClick={loadData} className="shrink-0 font-bold text-amber-800 hover:text-amber-950 underline">Retry</button>
        </div>
      )}
      {/* Active Tab Router */}
      {activeTab === "dashboard" && (
        !loading && products.length === 0 ? (
          <WorkspaceSetupPage
            currentRole={currentRole}
            onImportData={() => setActiveTab("data-quality")}
            onReady={loadData}
          />
        ) : (
          <ExecutiveDashboard
            summary={summary}
            loading={loading}
            onSelectProduct={setSelectedProductId}
            onNavigateToForecast={handleNavigateToForecast}
          />
        )
      )}

      {activeTab === "forecasting" && (
        <DemandForecastingPage
          products={products}
          initialProductId={forecastTargetProduct}
          currentRole={currentRole}
        />
      )}

      {activeTab === "inventory" && (
        <InventoryOptimizationPage
          recommendations={summary?.recommendations || []}
          products={products}
          onSelectProduct={setSelectedProductId}
          currentRole={currentRole}
        />
      )}

      {activeTab === "risk" && (
        <RiskMonitoringPage
          recommendations={summary?.recommendations || []}
          onSelectProduct={setSelectedProductId}
        />
      )}

      {activeTab === "products" && (
        <ProductsPage
          products={products}
          onSelectProduct={setSelectedProductId}
          onRefresh={loadData}
          currentRole={currentRole}
        />
      )}

      {activeTab === "history" && <ForecastHistoryPage />}

      {activeTab === "models" && <ModelRegistryPage currentRole={currentRole} />}

      {activeTab === "data-quality" && <DataQualityPage currentRole={currentRole} onDataImported={loadData} />}

      {activeTab === "system-health" && <SystemHealthPage />}

      {activeTab === "settings" && <SettingsPage />}

      {/* Product Intelligence Drawer */}
      <ProductDrawer
        productId={selectedProductId}
        onClose={() => setSelectedProductId(null)}
        onNavigateToForecast={handleNavigateToForecast}
        currentRole={currentRole}
        onInventoryChanged={loadData}
      />
    </AppShell>
  );
}

export default App;
