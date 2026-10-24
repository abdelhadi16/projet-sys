// ---------------------------------------------------------------------------
// KeyboardView — the Keyboard tab. Shows the live key-event feed, a rule editor
// and the observe/blocking mode switch. Talks to the keyboard API, or generates
// fake keystrokes with an in-memory rule store when `demo` is true.
//
// Important: the backend has no per-rule routes and no mode route. Every change
// (add/edit/delete/enable/disable/mode) is persisted by POSTing the WHOLE store
// via api.saveRules(observe_only, rules). We update local state first for a
// snappy UI, then save.
// ---------------------------------------------------------------------------

import { useEffect, useRef, useState } from "react";

import ConnectionStatus from "../components/ConnectionStatus.jsx";
import ModeSwitch from "../components/ModeSwitch.jsx";
import EventFeed from "../components/EventFeed.jsx";
import RuleEditor from "../components/RuleEditor.jsx";

import { useKeyboardSocket } from "../hooks/useKeyboardSocket.js";
import * as api from "../lib/api.js";
import { demoStarterRules, startDemoKeyStream } from "../lib/keyboard.js";
import { MAX_FEED_EVENTS } from "../config.js";

export default function KeyboardView({ demo }) {
  const [events, setEvents] = useState([]); // newest first
  const [rules, setRules] = useState([]);
  const [observeOnly, setObserveOnly] = useState(true); // safe default
  const [error, setError] = useState(null);

  // Add one event to the front of the feed, capped so it never grows forever.
  function pushEvent(log) {
    setEvents((prev) => [log, ...prev].slice(0, MAX_FEED_EVENTS));
  }

  // Live key events + initial state over the WebSocket (idle in demo mode).
  const status = useKeyboardSocket({
    enabled: !demo,
    onKeyEvent: pushEvent,
    onInitialState: (msg) => {
      if (Array.isArray(msg.rules)) setRules(msg.rules);
      if (typeof msg.observe_only === "boolean") setObserveOnly(msg.observe_only);
    },
  });

  // One REST fetch on connect so the rules show even before INITIAL_STATE.
  useEffect(() => {
    if (demo) return;
    api
      .getRules()
      .then((data) => {
        setRules(data.rules || []);
        if (typeof data.observe_only === "boolean") setObserveOnly(data.observe_only);
        setError(null);
      })
      .catch(() =>
        setError("Backend not reachable. Turn on Demo mode to preview the UI.")
      );
  }, [demo]);

  // Demo mode: fake key stream + starter rules. We read the latest rules/mode
  // from a ref so the stream reacts to edits without restarting.
  const stateRef = useRef({ rules, observeOnly });
  stateRef.current = { rules, observeOnly };
  useEffect(() => {
    if (!demo) return;
    setRules(demoStarterRules());
    setEvents([]);
    return startDemoKeyStream(() => stateRef.current, pushEvent);
  }, [demo]);

  // Persist the whole store to the backend (no-op in demo mode).
  function save(nextObserveOnly, nextRules) {
    if (demo) return;
    api.saveRules(nextObserveOnly, nextRules).catch(() =>
      setError("Could not save rules to the backend.")
    );
  }

  // --- Handlers: update local state, then save the full store ------------
  function handleModeChange(next) {
    setObserveOnly(next);
    save(next, rules);
  }
  function handleCreate(rule) {
    const next = [...rules, rule];
    setRules(next);
    save(observeOnly, next);
  }
  function handleUpdate(id, rule) {
    const next = rules.map((r) => (r.id === id ? rule : r));
    setRules(next);
    save(observeOnly, next);
  }
  function handleDelete(id) {
    const next = rules.filter((r) => r.id !== id);
    setRules(next);
    save(observeOnly, next);
  }

  return (
    <>
      <div className="subbar">
        <ConnectionStatus status={status} demo={demo} />
        <ModeSwitch observeOnly={observeOnly} onChange={handleModeChange} />
      </div>

      {error && !demo && <div className="banner">{error}</div>}

      <div className="columns">
        <EventFeed events={events} />
        <RuleEditor
          rules={rules}
          onCreate={handleCreate}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
        />
      </div>
    </>
  );
}
