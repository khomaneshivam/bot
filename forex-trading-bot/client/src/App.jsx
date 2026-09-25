/**
 * QuantAI Autonomous Forex & Crypto Terminal
 * Root React Application Entrypoint
 */

import React from "react";
import { TradingProvider } from "./context/TradingContext";
import { Dashboard } from "./pages/Dashboard";

export default function App() {
  return (
    <TradingProvider>
      <Dashboard />
    </TradingProvider>
  );
}
