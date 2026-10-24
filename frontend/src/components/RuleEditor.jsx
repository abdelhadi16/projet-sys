// The rules panel: lists rules and lets you add, edit, enable/disable and
// delete them. It is "dumb" about persistence — the parent (KeyboardView)
// passes the rules in and the callbacks that save them (which POST the whole
// store to the backend, or mutate the in-memory list in demo mode).
import { useState } from "react";
import RuleForm from "./RuleForm.jsx";
import { describeRule } from "../lib/keyboard.js";

export default function RuleEditor({ rules, onCreate, onUpdate, onDelete }) {
  // "new" = adding, an id = editing that rule, null = just viewing.
  const [editing, setEditing] = useState(null);

  function handleSave(rule) {
    if (editing === "new") onCreate(rule);
    else onUpdate(rule.id, rule);
    setEditing(null);
  }

  return (
    <section className="panel">
      <h2>Rules</h2>

      {editing === "new" && (
        <RuleForm onSave={handleSave} onCancel={() => setEditing(null)} />
      )}

      {rules.length === 0 && editing !== "new" && (
        <div className="empty">No rules yet. Add one to block or remap a key.</div>
      )}

      {rules.map((rule) =>
        editing === rule.id ? (
          <RuleForm
            key={rule.id}
            initial={rule}
            onSave={handleSave}
            onCancel={() => setEditing(null)}
          />
        ) : (
          <div key={rule.id} className={`rule ${rule.enabled ? "" : "disabled"}`}>
            <div className="rule-head">
              <span className="rule-title">{rule.id}</span>
              <div className="row-actions">
                <button
                  className="btn small"
                  onClick={() => onUpdate(rule.id, { ...rule, enabled: !rule.enabled })}
                >
                  {rule.enabled ? "Disable" : "Enable"}
                </button>
                <button className="btn small" onClick={() => setEditing(rule.id)}>
                  Edit
                </button>
                <button className="btn small danger" onClick={() => onDelete(rule.id)}>
                  Delete
                </button>
              </div>
            </div>
            <div className="rule-body">{describeRule(rule)}</div>
          </div>
        )
      )}

      {editing === null && (
        <button className="btn primary" onClick={() => setEditing("new")}>
          + Add rule
        </button>
      )}
    </section>
  );
}
