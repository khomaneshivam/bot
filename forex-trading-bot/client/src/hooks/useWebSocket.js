import { useState, useEffect, useRef, useCallback } from "react";

export function useWebSocket(onMessageCallback, token) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("CONNECTING");
  const [lastMessageTime, setLastMessageTime] = useState(null);
  const [latencyMs, setLatencyMs] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const pingTimestampRef = useRef(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host || "localhost:8000";
    const currentToken = token || (typeof localStorage !== "undefined" ? localStorage.getItem("quant_auth_token") : null);
    const wsUrl = `${protocol}//${host}/ws${currentToken ? `?token=${encodeURIComponent(currentToken)}` : ""}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setConnectionStatus("CONNECTED");
        setLastMessageTime(new Date());

        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }

        // Start heartbeat ping
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            pingTimestampRef.current = Date.now();
            ws.send("ping");
          }
        }, 10000);
      };

      ws.onmessage = (event) => {
        setLastMessageTime(new Date());

        if (event.data === "pong") {
          if (pingTimestampRef.current) {
            setLatencyMs(Date.now() - pingTimestampRef.current);
          }
          return;
        }

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
        setConnectionStatus("RECONNECTING");
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 2500);
      };

      ws.onerror = (err) => {
        console.warn("[useWebSocket] Socket error event:", err);
        ws.close();
      };
    } catch (err) {
      console.error("[useWebSocket] Connection init failure:", err);
      setConnectionStatus("DISCONNECTED");
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    }
  }, [onMessageCallback, token]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  // When token updates dynamically, authenticate over existing connection if open
  useEffect(() => {
    if (token && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "auth", token }));
    }
  }, [token]);

  return {
    isConnected,
    connectionStatus,
    lastMessageTime,
    latencyMs,
  };
}
