// Toggle between "observe-only" (log but never block) and "blocking" (rules are
// enforced). Maps to RuleStore.observe_only in takekbctrl.py. On the real
// backend, flipping this POSTs the whole rule store with the new observe_only.
export default function ModeSwitch({ observeOnly, onChange, disabled }) {
  // The toggle reads "on" when BLOCKING is active (observe_only off), the
  // stronger, more notable state.
  const blocking = !observeOnly;

  return (
    <span className="mode-switch">
      <span>{blocking ? "Blocking" : "Observe only"}</span>
      <button
        type="button"
        className={`toggle ${blocking ? "on" : ""}`}
        onClick={() => onChange(!observeOnly)}
        disabled={disabled}
        aria-pressed={blocking}
        aria-label="Toggle blocking mode"
      >
        <span className="knob" />
      </button>
    </span>
  );
}
