/**
 * QuantAI Terminal - Main Dashboard Page
 * High-tech layout combining Left Sidebar, Top Header, and Dynamic View Panels
 */

import React from "react";
import { useTrading } from "../context/TradingContext";
import { Sidebar } from "../components/Sidebar";
import { Header } from "../components/Header";
import { TerminalView } from "../components/TerminalView";
import { AllTradesLedger } from "../components/AllTradesLedger";
import { ScannerView } from "../components/ScannerView";
import { AIStudioView } from "../components/AIStudioView";
import { MacroView } from "../components/MacroView";
import NewsCatalystView from "../components/NewsCatalystView";
import PsychologyView from "../components/PsychologyView";

export function Dashboard() {
  const { activeView } = useTrading();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-obsidian-950 text-slate-100 antialiased select-none">
      {/* Left Institutional Navigation Sidebar */}
      <Sidebar />

      {/* Main Viewport Container */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-obsidian-950">
        {/* Top Navbar Header */}
        <Header />

        {/* Dynamic View Router */}
        <main className="flex-1 flex flex-col overflow-hidden relative">
          {activeView === "terminal" && <TerminalView />}
          {activeView === "ledger" && <AllTradesLedger />}
          {activeView === "scanner" && <ScannerView />}
          {activeView === "news" && <NewsCatalystView />}
          {activeView === "psychology" && <PsychologyView />}
          {activeView === "ai-studio" && <AIStudioView />}
          {activeView === "macro" && <MacroView />}
        </main>
      </div>
    </div>
  );
}
