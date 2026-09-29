import React from "react";
import { useTrading } from "../../context/TradingContext";
import { AlertBanner } from "../common/AlertBanner";

export function GlobalAlerts() {
  const { telemetry, reconciliationData, resetCircuitBreakersSafe, setActiveView } = useTrading();
  const { circuit_breakers, broker_connected, account } = telemetry;

  const isDesynced = reconciliationData.has_active_mismatch;
  const isTripped = circuit_breakers?.tripped;
  const isDrawdownBreached = account?.daily_drawdown_limit_hit;
  const isBrokerDisconnected = !broker_connected;

  return (
    <div className="flex flex-col select-none">
      {/* 1. Critical Reconciliation Desync */}
      {isDesynced && (
        <AlertBanner
          severity="CRITICAL"
          title="BROKER RECONCILIATION MISMATCH DETECTED · NEW ENTRIES HALTED"
          message="Internal active positions differ from authoritative broker truth. Check reconciliation console immediately."
          actionLabel="View Reconciliation"
          onAction={() => setActiveView("reconciliation")}
        />
      )}

      {/* 2. Broker Disconnection */}
      {isBrokerDisconnected && (
        <AlertBanner
          severity="CRITICAL"
          title="BROKER ADAPTER DISCONNECTED"
          message="Execution connection to MetaTrader 5 / Binance is offline. Orders cannot be filled."
          actionLabel="View System Health"
          onAction={() => setActiveView("system")}
        />
      )}

      {/* 3. Hard Circuit Breakers Tripped */}
      {isTripped && (
        <AlertBanner
          severity="CRITICAL"
          title="RISK CIRCUIT BREAKER TRIPPED · EXECUTION FROZEN"
          message={
            Object.entries(circuit_breakers?.active_breakers || {})
              .map(([name, reason]) => `${name}: ${reason}`)
              .join(" | ") || "Autonomous order generation is locked."
          }
          actionLabel="Reset Breakers"
          onAction={resetCircuitBreakersSafe}
        />
      )}

      {/* 4. Daily Drawdown Limit Breach */}
      {isDrawdownBreached && !isTripped && (
        <AlertBanner
          severity="WARNING"
          title="DAILY DRAWDOWN LIMIT REACHED"
          message="Portfolio has hit maximum daily drawdown threshold. New entries blocked until midnight UTC rollover."
          actionLabel="View Risk"
          onAction={() => setActiveView("risk")}
        />
      )}
    </div>
  );
}
