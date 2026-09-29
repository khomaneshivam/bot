import React from "react";
import { useTrading } from "../context/TradingContext";
import { TopBar } from "../components/layout/TopBar";
import { Sidebar } from "../components/layout/Sidebar";
import { GlobalAlerts } from "../components/layout/GlobalAlerts";
import { SystemStatusBar } from "../components/layout/SystemStatusBar";
import { ConfirmDialog } from "../components/common/ConfirmDialog";
import { LoginModal } from "../components/common/LoginModal";
import { ProfileModal } from "../components/common/ProfileModal";

// 12 First-Class Feature Views
import { DashboardView } from "../features/dashboard/DashboardView";
import { MarketsView } from "../features/markets/MarketsView";
import { PositionsView } from "../features/positions/PositionsView";
import { OrdersView } from "../features/orders/OrdersView";
import { StrategiesView } from "../features/strategies/StrategiesView";
import { MLObservabilityView } from "../features/ml/MLObservabilityView";
import { RiskView } from "../features/risk/RiskView";
import { NewsMacroView } from "../features/news/NewsMacroView";
import { ExecutionView } from "../features/execution/ExecutionView";
import { ReconcileView } from "../features/reconciliation/ReconcileView";
import { SystemHealthView } from "../features/system/SystemHealthView";
import { AuditTimelineView } from "../features/audit/AuditTimelineView";

export function Dashboard() {
  const { activeView, confirmModal, closeConfirmModal } = useTrading();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 antialiased select-none font-sans">
      {/* Institutional Left Sidebar */}
      <Sidebar />

      {/* Main Viewport Workspace */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-950">
        {/* Top Header */}
        <TopBar />

        {/* Global High-Priority Alerts (Reconciliation, Circuit Breakers, Disconnects) */}
        <GlobalAlerts />

        {/* Dynamic 12-View Workspace */}
        <main className="flex-1 flex flex-col overflow-hidden relative">
          {activeView === "dashboard" && <DashboardView />}
          {activeView === "markets" && <MarketsView />}
          {activeView === "positions" && <PositionsView />}
          {activeView === "orders" && <OrdersView />}
          {activeView === "strategies" && <StrategiesView />}
          {activeView === "ml" && <MLObservabilityView />}
          {activeView === "risk" && <RiskView />}
          {activeView === "news" && <NewsMacroView />}
          {activeView === "execution" && <ExecutionView />}
          {activeView === "reconciliation" && <ReconcileView />}
          {activeView === "system" && <SystemHealthView />}
          {activeView === "audit" && <AuditTimelineView />}
        </main>

        {/* Persistent Bottom System Status Bar */}
        <SystemStatusBar />
      </div>

      {/* Privileged Action Multi-Step Confirmation Modal */}
      <ConfirmDialog
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        description={confirmModal.description}
        warningNote={confirmModal.warningNote}
        confirmWord={confirmModal.confirmWord}
        confirmVariant={confirmModal.confirmVariant}
        checklist={confirmModal.checklist}
        onConfirm={confirmModal.onConfirm}
        onCancel={closeConfirmModal}
      />

      {/* RBAC Login Modal */}
      <LoginModal />

      {/* Operator Security Profile Modal */}
      <ProfileModal />
    </div>
  );
}
