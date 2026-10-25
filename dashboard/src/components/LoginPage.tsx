import React, { useState } from "react";
import {
  Lock,
  User as UserIcon,
  Eye,
  EyeOff,
  AlertCircle,
  ArrowRight,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { api, setStoredToken, getStoredToken } from "../lib/api";
import { User } from "../types";

export interface LoginPageProps {
  onLoginSuccess: (user: User, token: string) => void;
  onCancel?: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess, onCancel }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const trimmedUsername = username.trim();
    if (!trimmedUsername || !password || (mode === "register" && !organizationName.trim())) {
      setErrorMessage(mode === "register" ? "Enter an organisation name, username, and password." : "Enter your username and password.");
      return;
    }
    if (mode === "register" && !/^[A-Za-z0-9_.-]+$/.test(trimmedUsername)) {
      setErrorMessage("Username can contain only letters, numbers, dots, underscores, and hyphens—no spaces.");
      return;
    }
    if (mode === "register" && password.length < 12) {
      setErrorMessage("Choose a password with at least 12 characters for workspace security.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const user = mode === "register"
        ? await api.register(organizationName.trim(), trimmedUsername, password)
        : await api.login(trimmedUsername, password);

      if (!user || !user.token) {
        throw new Error("Invalid response from authentication service.");
      }

      // Persist session token using the Step 1 storage utility
      setStoredToken(user.token);

      // Verify that the token was successfully persisted in browser storage
      const stored = getStoredToken();
      if (stored !== user.token) {
        setErrorMessage(
          "Unable to persist authentication token in browser storage. Please verify that storage/cookies are enabled."
        );
        return;
      }

      // Notify parent application with authenticated user and token
      onLoginSuccess(user, user.token);
    } catch (err: unknown) {
      const rawMessage = err instanceof Error ? err.message : String(err);

      // Protect user privacy: normalize credential errors without disclosing whether the username exists
      if (
        rawMessage.toLowerCase().includes("invalid") ||
        rawMessage.toLowerCase().includes("credential") ||
        rawMessage.toLowerCase().includes("unauthorized") ||
        rawMessage.includes("401")
      ) {
        setErrorMessage("Invalid username or password. Please verify your credentials and try again.");
      } else {
        setErrorMessage(rawMessage || "We could not complete that request. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F6F8FC] text-slate-900 flex flex-col selection:bg-blue-600 selection:text-white">
      {/* Top Navbar Header */}
      <header className="h-16 border-b border-slate-200/80 bg-white/70 backdrop-blur-md px-6 lg:px-16 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
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

        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
          >
            Back to Home
          </button>
        )}
      </header>

      {/* Main Login Card Section */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-8">
        <div className="card max-w-md w-full p-6 sm:p-8 space-y-6">
          {/* Form Header */}
          <div className="space-y-2 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 border border-blue-100 mx-auto mb-1">
              <Lock className="w-5 h-5" />
            </div>
            <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
              {mode === "register" ? "Create your workspace" : "Sign In to DemandIQ"}
            </h1>
            <p className="text-xs sm:text-sm text-slate-500">
              {mode === "register" ? "Create a private workspace for your organization. You will be its first administrator." : "Enter your credentials to access demand forecasting and inventory intelligence."}
            </p>
          </div>

          {/* Accessible Error Alert */}
          {errorMessage && (
            <div
              role="alert"
              aria-live="polite"
              className="p-3.5 rounded-xl bg-rose-50 border border-rose-200/90 text-rose-800 flex items-start gap-2.5 text-xs animate-in fade-in duration-150"
            >
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1 font-medium leading-relaxed">{errorMessage}</div>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {mode === "register" && (
              <div className="space-y-1.5">
                <label htmlFor="organization-name" className="block text-xs font-bold text-slate-700">Organization name</label>
                <input id="organization-name" type="text" disabled={isLoading} value={organizationName} onChange={(e) => setOrganizationName(e.target.value)} placeholder="Example Retail Pvt Ltd" className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-white text-xs sm:text-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600" />
              </div>
            )}
            {/* Username Input */}
            <div className="space-y-1.5">
              <label
                htmlFor="login-username"
                className="block text-xs font-bold text-slate-700"
              >
                Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <UserIcon className="w-4 h-4" />
                </div>
                <input
                  id="login-username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  autoFocus
                  disabled={isLoading}
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    if (errorMessage) setErrorMessage(null);
                  }}
                  placeholder="Enter your username"
                  aria-invalid={Boolean(errorMessage)}
                  className="w-full pl-9 pr-3.5 py-2.5 rounded-xl border border-slate-200 bg-white text-xs sm:text-sm font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            {/* Password Input */}
            <div className="space-y-1.5">
              <label
                htmlFor="login-password"
                className="block text-xs font-bold text-slate-700"
              >
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  disabled={isLoading}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (errorMessage) setErrorMessage(null);
                  }}
                  placeholder="Enter your password"
                  aria-invalid={Boolean(errorMessage)}
                  className="w-full pl-9 pr-10 py-2.5 rounded-xl border border-slate-200 bg-white text-xs sm:text-sm font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                  tabIndex={-1}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading || !username.trim() || !password || (mode === "register" && !organizationName.trim())}
                className="btn-primary w-full py-3 justify-center text-xs sm:text-sm font-bold shadow-md shadow-blue-500/25 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>{mode === "register" ? "Creating workspace..." : "Signing in..."}</span>
                  </>
                ) : (
                  <>
                    <span>{mode === "register" ? "Create workspace" : "Sign In"}</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>

          <button type="button" disabled={isLoading} onClick={() => { setMode(mode === "login" ? "register" : "login"); setErrorMessage(null); }} className="w-full text-xs font-bold text-blue-700 hover:text-blue-900">
            {mode === "login" ? "New here? Create a private workspace" : "Already have an account? Sign in"}
          </button>

          {/* Security & Access Notice */}
          <div className="pt-4 border-t border-slate-100 flex items-center justify-center gap-2 text-[11px] text-slate-500 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Role-Based Access Control Protected</span>
          </div>
        </div>
      </main>
    </div>
  );
};
