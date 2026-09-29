/**
 * QuantAI Autonomous Forex & Crypto Terminal
 * Root Application Entrypoint with Institutional Authentication Gate
 */

import React from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { TradingProvider } from "./context/TradingContext";
import { Dashboard } from "./pages/Dashboard";
import { AuthPage } from "./features/auth/AuthPage";

function TerminalApp() {
  const { isAuthenticated, isGuest, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="h-screen w-screen bg-slate-950 flex flex-col items-center justify-center text-slate-400 font-mono text-xs gap-3 select-none">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center font-black text-white text-base shadow-xl shadow-sky-500/20 animate-pulse">
          Q
        </div>
        <div className="flex items-center gap-2 text-slate-300">
          <div className="w-3 h-3 border-2 border-sky-400 border-t-transparent rounded-full animate-spin" />
          <span>Verifying cryptographic security session...</span>
        </div>
      </div>
    );
  }

  // Gate unauthenticated visitors with the institutional AuthPage from the beginning
  if (!isAuthenticated && !isGuest) {
    return <AuthPage />;
  }

  return (
    <TradingProvider>
      <Dashboard />
    </TradingProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <TerminalApp />
    </AuthProvider>
  );
}
