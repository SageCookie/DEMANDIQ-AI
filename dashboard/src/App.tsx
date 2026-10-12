import React, { useState, useEffect } from "react";
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
import { ProductDrawer } from "./components/ProductDrawer";
import { DashboardSummary, Product, UserRole } from "./types";
import { api } from "./lib/api";

export function App() {
  const [showLanding, setShowLanding] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");
  const [currentRole, setCurrentRole] = useState<UserRole>("ADMIN");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [forecastTargetProduct, setForecastTargetProduct] = useState<string>("P001");

  const loadData = async () => {
    setIsRefreshing(true);
    try {
      const [sumRes, prodRes] = await Promise.all([
        api.getDashboardSummary(),
        api.getProducts(),
      ]);
      setSummary(sumRes);
      setProducts(prodRes);
    } catch (err) {
      console.error("Error fetching data:", err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleNavigateToForecast = (productId: string) => {
    setForecastTargetProduct(productId);
    setActiveTab("forecasting");
    setSelectedProductId(null);
  };

  if (showLanding) {
    return (
      <LandingPage
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
      currentRole={currentRole}
      onRoleChange={setCurrentRole}
      onRefresh={loadData}
      isRefreshing={isRefreshing}
      onOpenLanding={() => setShowLanding(true)}
    >
      {/* Active Tab Router */}
      {activeTab === "dashboard" && (
        <ExecutiveDashboard
          summary={summary}
          loading={loading}
          onSelectProduct={setSelectedProductId}
          onNavigateToForecast={handleNavigateToForecast}
        />
      )}

      {activeTab === "forecasting" && (
        <DemandForecastingPage
          products={products}
          initialProductId={forecastTargetProduct}
        />
      )}

      {activeTab === "inventory" && (
        <InventoryOptimizationPage
          recommendations={summary?.recommendations || []}
          products={products}
          onSelectProduct={setSelectedProductId}
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
        />
      )}

      {activeTab === "history" && <ForecastHistoryPage />}

      {activeTab === "models" && <ModelRegistryPage />}

      {activeTab === "data-quality" && <DataQualityPage />}

      {activeTab === "system-health" && <SystemHealthPage />}

      {activeTab === "settings" && <SettingsPage />}

      {/* Product Intelligence Drawer */}
      <ProductDrawer
        productId={selectedProductId}
        onClose={() => setSelectedProductId(null)}
        onNavigateToForecast={handleNavigateToForecast}
      />
    </AppShell>
  );
}

export default App;
