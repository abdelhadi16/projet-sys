// ---------------------------------------------------------------------------
// REST client for the FastAPI backend (Member 1 / Kenza, ../main.py).
//
// Each function maps to one HTTP route documented in API_CONTRACT.md. They
// return parsed JSON and throw on a non-2xx response so the UI can react. Live
// data comes over the WebSockets instead (see the hooks/ folder).
// ---------------------------------------------------------------------------

import { API_BASE } from "../config.js";

async function request(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`${options.method || "GET"} ${path} failed: ${res.status}`);
  }
  const text = await res.text();
  return text ? JSON.parse(text) : {};
}

// --- Devices ---------------------------------------------------------------

// GET /api/devices        -> { count, devices: [...] }
// GET /api/devices?class_filter=Keyboard  (optional server-side class filter)
export function getDevices(classFilter) {
  const query = classFilter
    ? `?class_filter=${encodeURIComponent(classFilter)}`
    : "";
  return request(`/api/devices${query}`);
}

// GET /api/devices/{instance_id} -> one device, or 404
export function getDevice(instanceId) {
  return request(`/api/devices/${encodeURIComponent(instanceId)}`);
}

// --- Keyboard rules --------------------------------------------------------

// GET /api/rules -> { observe_only, version, rules: [Rule] }
export function getRules() {
  return request("/api/rules");
}

// POST /api/rules replaces the WHOLE rule store at once (the backend has no
// per-rule routes and no separate mode route). So every change — add, edit,
// delete, enable/disable, or toggling observe-only — sends the full store.
// Body: { observe_only, rules: [Rule] }  ->  { status, version }
export function saveRules(observeOnly, rules) {
  return request("/api/rules", {
    method: "POST",
    body: JSON.stringify({ observe_only: observeOnly, rules }),
  });
}
