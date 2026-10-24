// ---------------------------------------------------------------------------
// Pure helpers + demo engine for the Keyboard view. No React, no side effects,
// so the formatting and the rule-matching logic can be unit-tested directly
// (see src/test/keyboard.test.js).
//
// A key "event" is one LogEntry.to_dict() from takekbctrl.py, delivered over
// the /ws/keyboard WebSocket inside { type: "KEY_EVENT", data: <here> }:
//   { enriched_event: { decoded: {raw, key_name, character, modifiers}, context },
//     verdict: { action, rule_id, replacement_key }, logged_at }
// ---------------------------------------------------------------------------

// ---- Formatting -----------------------------------------------------------

// A stable-ish React key for a log line.
export function eventKey(log) {
  const raw = log?.enriched_event?.decoded?.raw ?? {};
  return `${raw.timestamp}-${raw.key_code}-${raw.event_type}`;
}

// "SHIFT","CTRL" -> "Shift+Ctrl"; empty list -> "".
export function formatModifiers(modifiers) {
  if (!modifiers || modifiers.length === 0) return "";
  const pretty = { SHIFT: "Shift", CTRL: "Ctrl", ALT: "Alt", WIN: "Win", CAPS_LOCK: "Caps" };
  return modifiers.map((m) => pretty[m] || m).join("+");
}

// Make control characters visible in the feed.
export function displayCharacter(character) {
  if (character === undefined || character === null || character === "") return "";
  if (character === " ") return "␣";
  if (character === "\n") return "⏎";
  if (character === "\t") return "⇥";
  return character;
}

// POSIX seconds (Python time.time()) -> "HH:MM:SS.mmm".
export function formatTime(timestampSeconds) {
  if (!timestampSeconds) return "";
  const d = new Date(timestampSeconds * 1000);
  const p = (n, w = 2) => String(n).padStart(w, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`;
}

// One-line human summary of a rule for the rule list.
export function describeRule(rule) {
  const keys = rule.match_key?.length ? rule.match_key.join(", ") : "any key";
  let text = `${rule.action} ${keys}`;
  if (rule.match_modifiers?.length) text += ` with ${formatModifiers(rule.match_modifiers)}`;
  if (rule.match_process) text += ` (when in ${rule.match_process})`;
  if (rule.action === "MODIFY" && rule.replacement_key != null) {
    text += ` -> key ${rule.replacement_key}`;
  }
  return text;
}

// ---- Rule engine (mirrors decide_action() in takekbctrl.py) ---------------

// Decide what the rules engine would do for a decoded event. Rules are tried in
// priority order (highest first); the first enabled rule whose conditions all
// match wins. Used by demo mode so fake events get realistic verdicts.
export function decideVerdict(decoded, context, rules, observeOnly) {
  if (observeOnly) return { action: "PASS", rule_id: "observe_only", replacement_key: null };
  const sorted = [...rules].sort((a, b) => b.priority - a.priority);
  for (const rule of sorted) {
    if (!rule.enabled) continue;
    if (rule.match_key?.length && !rule.match_key.includes(decoded.key_name)) continue;
    if (rule.match_process && context.process_name !== rule.match_process) continue;
    if (rule.match_modifiers?.length) {
      const held = new Set(decoded.modifiers);
      if (!rule.match_modifiers.every((m) => held.has(m))) continue;
    }
    return { action: rule.action, rule_id: rule.id, replacement_key: rule.replacement_key ?? null };
  }
  return { action: "PASS", rule_id: null, replacement_key: null };
}

// ---- Demo mode ------------------------------------------------------------

const SAMPLE_KEYS = [
  { key_code: 72, key_name: "H", character: "h" },
  { key_code: 69, key_name: "E", character: "e" },
  { key_code: 76, key_name: "L", character: "l" },
  { key_code: 79, key_name: "O", character: "o" },
  { key_code: 32, key_name: "SPACE", character: " " },
  { key_code: 87, key_name: "W", character: "w" },
  { key_code: 82, key_name: "R", character: "r" },
  { key_code: 68, key_name: "D", character: "d" },
  { key_code: 91, key_name: "LWIN", character: "" },
  { key_code: 13, key_name: "ENTER", character: "\n" },
];

const SAMPLE_CONTEXTS = [
  { window_title: "Untitled - Notepad", process_name: "notepad.exe", process_id: 4821 },
  { window_title: "Terminal", process_name: "cmd.exe", process_id: 1033 },
  { window_title: "Project — VS Code", process_name: "code.exe", process_id: 7700 },
];

// Build one fake LogEntry-shaped event. `i` drives which sample is used, so the
// output is deterministic and testable.
export function makeDemoKeyEvent(i, rules, observeOnly) {
  const sample = SAMPLE_KEYS[i % SAMPLE_KEYS.length];
  const context = SAMPLE_CONTEXTS[i % SAMPLE_CONTEXTS.length];
  const now = Date.now() / 1000;
  const decoded = {
    raw: { key_code: sample.key_code, scan_code: 0, event_type: "PRESS", timestamp: now, is_injected: false },
    key_name: sample.key_name,
    character: sample.character,
    modifiers: [],
  };
  const verdict = decideVerdict(decoded, context, rules, observeOnly);
  return { enriched_event: { decoded, context }, verdict, logged_at: now };
}

// A starter rule so demo mode shows a blocked key out of the box.
export function demoStarterRules() {
  return [
    {
      id: "block-win-key",
      enabled: true,
      priority: 10,
      match_key: ["LWIN", "RWIN"],
      match_modifiers: [],
      match_process: null,
      action: "BLOCK",
      replacement_key: null,
    },
  ];
}

// Start a fake key-event stream. Calls onEvent(log) every intervalMs. getState()
// supplies the current rules/mode so verdicts react to edits. Returns stop().
export function startDemoKeyStream(getState, onEvent, intervalMs = 700) {
  let i = 0;
  const id = setInterval(() => {
    const { rules, observeOnly } = getState();
    onEvent(makeDemoKeyEvent(i, rules, observeOnly));
    i += 1;
  }, intervalMs);
  return () => clearInterval(id);
}
