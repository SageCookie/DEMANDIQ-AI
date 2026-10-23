import {
  Product,
  ForecastResponse,
  InventoryRecommendation,
  DashboardSummary,
  SystemStatus,
  DataQualityReport,
  User,
} from "../types";

// Local Docker uses the same origin. Hosted builds receive the public API URL
// at build time through VITE_API_BASE_URL.
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");
const TOKEN_KEY = "demandiq_auth_token";

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Ignore storage quota errors or disabled localStorage
  }
}

export function clearStoredToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Ignore storage errors
  }
}

type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function onUnauthorized(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = getStoredToken();
  const isAuthEndpoint = endpoint === "/auth/login";

  const authHeaders: Record<string, string> = {};
  if (token && !isAuthEndpoint) {
    authHeaders["Authorization"] = `Bearer ${token}`;
  }

  const isFormData = options?.body instanceof FormData;
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...authHeaders,
      ...options?.headers,
    },
  });

  if (!res.ok) {
    if (res.status === 401 && !isAuthEndpoint) {
      clearStoredToken();
      unauthorizedHandler?.();
    }

    let errorDetail = "API Request failed";
    try {
      const errJson = await res.json();
      errorDetail = errJson?.error?.message || errJson?.detail?.message || JSON.stringify(errJson);
    } catch {
      errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorDetail);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export const api = {
  getStoredToken,
  setStoredToken,
  clearStoredToken,
  onUnauthorized,
  getHealth: () => request<{ status: string; version: string }>("/health"),
  getSystemStatus: () => request<SystemStatus>("/system/status"),
  getDashboardSummary: () => request<DashboardSummary>("/dashboard/summary"),
  getProducts: (category?: string) =>
    request<Product[]>(`/products${category ? `?category=${encodeURIComponent(category)}` : ""}`),
  getProduct: (productId: string) => request<Product>(`/products/${productId}`),
  createProduct: (data: Partial<Product> & { initial_inventory?: number }) =>
    request<Product>("/products", { method: "POST", body: JSON.stringify(data) }),
  updateProduct: (productId: string, data: Partial<Product>) =>
    request<Product>(`/products/${productId}`, { method: "PUT", body: JSON.stringify(data) }),
  generateForecast: (productId: string, horizonDays: number = 30) =>
    request<ForecastResponse>("/forecasts", {
      method: "POST",
      body: JSON.stringify({ product_id: productId, horizon_days: horizonDays }),
    }),
  getForecastHistory: (productId?: string) =>
    request<any[]>(`/forecasts/history${productId ? `?product_id=${productId}` : ""}`),
  getRecommendations: (risk?: string, category?: string) => {
    const params = new URLSearchParams();
    if (risk) params.set("risk", risk);
    if (category) params.set("category", category);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<InventoryRecommendation[]>(`/inventory/recommendations${qs}`);
  },
  getProductOptimization: (productId: string) =>
    request<any>(`/inventory/optimization/${productId}`),
  adjustInventory: (productId: string, quantityDelta: number, reason: string, note?: string) =>
    request<any>(`/inventory/${productId}/adjustments`, { method: "POST", body: JSON.stringify({ quantity_delta: quantityDelta, reason, note }) }),
  getInventoryAdjustments: (productId: string) => request<any[]>(`/inventory/${productId}/adjustments`),
  createPurchaseOrder: (productId: string, quantity: number, expectedArrivalDate?: string, note?: string) =>
    request<any>("/purchase-orders", { method: "POST", body: JSON.stringify({ product_id: productId, quantity, expected_arrival_date: expectedArrivalDate || null, note }) }),
  getPurchaseOrders: (status?: string) => request<any[]>(`/purchase-orders${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  getModels: () => request<any[]>("/models"),
  getModelMetrics: (version: string) => request<any>(`/models/${version}/metrics`),
  triggerTrain: () => request<any>("/models/train", { method: "POST" }),
  getTrainingJob: (jobId: string) => request<any>(`/models/jobs/${jobId}`),
  getTrainingJobs: () => request<any[]>("/models/jobs"),
  promoteModel: (version: string) => request<any>(`/models/${version}/promote`, { method: "POST" }),
  getDataQuality: () => request<DataQualityReport>("/data/quality"),
  previewDataUpload: (file: File, defaultInventoryLevel: number, defaultLeadTimeDays: number) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("default_inventory_level", String(defaultInventoryLevel));
    formData.append("default_lead_time_days", String(defaultLeadTimeDays));
    return request<any>("/data/upload/preview", { method: "POST", body: formData });
  },
  confirmDataUpload: (uploadId: string) => request<any>(`/data/upload/${uploadId}/confirm`, { method: "POST" }),
  useDemoData: () => request<any>("/workspace/use-demo-data", { method: "POST" }),
  login: (username: string, password: string = "secret") =>
    request<User>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  getCurrentUser: () => request<User>("/auth/me"),
};
