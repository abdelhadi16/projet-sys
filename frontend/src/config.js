// ---------------------------------------------------------------------------
// Central configuration. Everything the frontend talks to lives here, so if the
// backend changes there is one place to edit.
//
// The backend is Kenza's FastAPI server in ../main.py, which serves BOTH a
// device API and a keyboard API. See API_CONTRACT.md for every route and
// WebSocket message this frontend consumes.
// ---------------------------------------------------------------------------

// Base URL of the FastAPI backend. Overridable at build time with VITE_API_BASE.
export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

// WebSocket URLs, derived from API_BASE by swapping http -> ws.
const WS_BASE = API_BASE.replace(/^http/, "ws");
export const WS_DEVICES_URL = WS_BASE + "/ws/devices"; // live device list
export const WS_KEYBOARD_URL = WS_BASE + "/ws/keyboard"; // live key events

// Keepalive interval (ms) for both sockets. The backend replies "pong".
export const PING_INTERVAL_MS = 20000;

// --- Keyboard domain constants (must match takekbctrl.py enums) ------------

// Verdict actions the rules engine can return.
export const ACTIONS = ["PASS", "BLOCK", "MODIFY", "INJECT"];

// Modifier keys the decoder reports.
export const MODIFIERS = ["SHIFT", "CTRL", "ALT", "WIN", "CAPS_LOCK"];

// Cap the live key-event feed so it stays responsive and bounded in memory.
export const MAX_FEED_EVENTS = 200;
