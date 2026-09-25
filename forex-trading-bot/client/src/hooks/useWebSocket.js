/**
 * QuantAI Terminal - Custom WebSocket Telemetry Hook
 * Manages resilient real-time streaming link with automatic reconnection
 */

import { useState, useEffect, useRef, useCallback } from "react";

export function useWebSocket(onMessageCallback) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("CONNECTING...");
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host || "localhost:8000";
    const wsUrl = `${protocol}//${host}/ws`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setConnectionStatus("STREAM ONLINE");
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (onMessageCallback) {
            onMessageCallback(payload);
          }
        } catch (err) {
          console.error("[useWebSocket] JSON parse error:", err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        setConnectionStatus("OFFLINE - RETRYING");
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 2500);
      };

      ws.onerror = (err) => {
        console.error("[useWebSocket] Socket error:", err);
        ws.close();
      };
    } catch (err) {
      console.error("[useWebSocket] Connection init failure:", err);
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    }
  }, [onMessageCallback]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { isConnected, connectionStatus };
}
