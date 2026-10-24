// ---------------------------------------------------------------------------
// useKeyboardSocket — React hook owning the WebSocket to the backend's live
// key-event stream (/ws/keyboard) and exposing a connection status.
//
// Messages (see API_CONTRACT.md / main.py):
//   { type: "INITIAL_STATE", rules: [...], observe_only: bool }  // on connect
//   { type: "KEY_EVENT", data: <LogEntry> }                      // per keystroke
//
// It reconnects automatically and sends a periodic "ping" keepalive. When
// `enabled` is false (demo mode on) it stays idle.
// ---------------------------------------------------------------------------

import { useEffect, useRef, useState } from "react";
import { WS_KEYBOARD_URL, PING_INTERVAL_MS } from "../config.js";

// status: "connecting" | "connected" | "disconnected"
export function useKeyboardSocket({ enabled, onKeyEvent, onInitialState }) {
  const [status, setStatus] = useState("disconnected");

  // Keep latest callbacks in refs so reconnection doesn't depend on them.
  const onKeyRef = useRef(onKeyEvent);
  const onInitRef = useRef(onInitialState);
  onKeyRef.current = onKeyEvent;
  onInitRef.current = onInitialState;

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
      ws = new WebSocket(WS_KEYBOARD_URL);

      ws.onopen = () => {
        setStatus("connected");
        pingTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send("ping");
        }, PING_INTERVAL_MS);
      };

      ws.onmessage = (ev) => {
        let msg;
        try {
          msg = JSON.parse(ev.data);
        } catch {
          return;
        }
        if (msg.type === "KEY_EVENT" && msg.data) {
          onKeyRef.current?.(msg.data);
        } else if (msg.type === "INITIAL_STATE") {
          onInitRef.current?.(msg);
        }
      };

      ws.onclose = () => {
        clearInterval(pingTimer);
        if (closedByUs) return;
        setStatus("disconnected");
        reconnectTimer = setTimeout(connect, 2000);
      };

      ws.onerror = () => ws.close();
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
