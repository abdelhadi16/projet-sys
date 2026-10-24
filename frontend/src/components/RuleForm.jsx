// Form for creating or editing a single rule. Controlled: its fields live in
// local state, and on save it hands a complete Rule object (matching
// takekbctrl.Rule) back to the parent.
import { useState } from "react";
import { ACTIONS, MODIFIERS } from "../config.js";

function emptyRule() {
  return {
    id: "",
    enabled: true,
    priority: 0,
    match_key: [],
    match_modifiers: [],
    match_process: "",
    action: "BLOCK",
    replacement_key: null,
  };
}

export default function RuleForm({ initial, onSave, onCancel }) {
  const [draft, setDraft] = useState(initial ? { ...initial } : emptyRule());

  function set(field, value) {
    setDraft((d) => ({ ...d, [field]: value }));
  }

  // match_key is a list in the data model but easier to type as a comma list.
  const matchKeyText = draft.match_key.join(", ");

  function toggleModifier(mod) {
    setDraft((d) => {
      const has = d.match_modifiers.includes(mod);
      return {
        ...d,
        match_modifiers: has
          ? d.match_modifiers.filter((m) => m !== mod)
          : [...d.match_modifiers, mod],
      };
    });
  }

  function handleSubmit(e) {
    e.preventDefault();
    // Normalise into the exact Rule shape the backend expects.
    const rule = {
      ...draft,
      id: draft.id.trim() || `rule-${Date.now()}`,
      priority: Number(draft.priority) || 0,
      match_key: matchKeyText.split(",").map((s) => s.trim()).filter(Boolean),
      match_process: (draft.match_process || "").trim() || null,
      replacement_key:
        draft.action === "MODIFY" && draft.replacement_key
          ? Number(draft.replacement_key)
          : null,
    };
    onSave(rule);
  }

  return (
    <form className="rule" onSubmit={handleSubmit}>
      <label>Rule name / id</label>
      <input
        type="text"
        placeholder="e.g. block-win-key"
        value={draft.id}
        onChange={(e) => set("id", e.target.value)}
      />

      <label>Keys to match (comma separated, e.g. LWIN, RWIN)</label>
      <input
        type="text"
        placeholder="leave empty to match any key"
        value={matchKeyText}
        onChange={(e) => set("match_key", e.target.value.split(","))}
      />

      <label>Required modifiers</label>
      <div className="checks">
        {MODIFIERS.map((mod) => (
          <label key={mod}>
            <input
              type="checkbox"
              checked={draft.match_modifiers.includes(mod)}
              onChange={() => toggleModifier(mod)}
            />
            {mod}
          </label>
        ))}
      </div>

      <label>Only in process (optional, e.g. notepad.exe)</label>
      <input
        type="text"
        placeholder="leave empty to match any app"
        value={draft.match_process || ""}
        onChange={(e) => set("match_process", e.target.value)}
      />

      <label>Action</label>
      <select value={draft.action} onChange={(e) => set("action", e.target.value)}>
        {ACTIONS.map((a) => (
          <option key={a} value={a}>
            {a}
          </option>
        ))}
      </select>

      {/* Replacement key only applies to MODIFY. */}
      {draft.action === "MODIFY" && (
        <>
          <label>Replacement key code (virtual-key code)</label>
          <input
            type="number"
            value={draft.replacement_key ?? ""}
            onChange={(e) => set("replacement_key", e.target.value)}
          />
        </>
      )}

      <label>Priority (higher wins first)</label>
      <input
        type="number"
        value={draft.priority}
        onChange={(e) => set("priority", e.target.value)}
      />

      <div className="form-actions">
        <button type="submit" className="btn primary">
          Save rule
        </button>
        <button type="button" className="btn" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
