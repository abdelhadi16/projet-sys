// ---------------------------------------------------------------------------
// useDeviceSocket — React hook that owns the WebSocket to the backend's live
// device-change stream (/ws/devices) and exposes a connection status.
//
// The backend sends the FULL device list on connect and again on every change
// (see main.py), so we simply replace our list each time rather than patching.
//
// It also:
//   - reconnects automatically if the backend drops
//   - sends a periodic "ping" keepalive (backend replies "pong")
//
// When `enabled` is false (demo mode on) the hook stays idle.
// ---------------------------------------------------------------------------

import { useEffect, useRef, useState } from "react";
import { WS_DEVICES_URL, PING_INTERVAL_MS } from "../config.js";

// status: "connecting" | "connected" | "disconnected"
export function useDeviceSocket({ enabled, onDevices }) {
  const [status, setStatus] = useState("disconnected");

  // Keep the latest callback in a ref so reconnection logic doesn't depend on
  // it (which would tear the socket down on every render).
  const onDevicesRef = useRef(onDevices);
  onDevicesRef.current = onDevices;

  useEffect(() => {
    if (!enabled) {
      setStatus("disconnected");
      return;
    }

    let ws;
    let reconnectTimer;
    let pingTimer;
    let closedByUs = false;

    function connect() {
      setStatus("connecting");
      ws = new WebSocket(WS_DEVICES_URL);

      ws.onopen = () => {
        setStatus("connected");
        // Keepalive so proxies / the server don't drop an idle connection.
        pingTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send("ping");
        }, PING_INTERVAL_MS);
      };

      ws.onmessage = (ev) => {
        let msg;
        try {
          msg = JSON.parse(ev.data);
        } catch {
          return; // ignore malformed frames
        }
        // INITIAL_STATE (on connect) and DEVICE_UPDATE (on change) both carry
        // the full device list. "pong" replies are ignored.
        if (
          (msg.type === "INITIAL_STATE" || msg.type === "DEVICE_UPDATE") &&
          Array.isArray(msg.devices)
        ) {
          onDevicesRef.current?.(msg.devices);
        }
      };

      ws.onclose = () => {
        clearInterval(pingTimer);
        if (closedByUs) return;
        setStatus("disconnected");
        // Retry so a backend restart reconnects without a page refresh.
        reconnectTimer = setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        ws.close(); // onclose handles the reconnect
      };
    }

    connect();

    return () => {
      closedByUs = true;
      clearTimeout(reconnectTimer);
      clearInterval(pingTimer);
      if (ws) ws.close();
    };
  }, [enabled]);

  return status;
}
