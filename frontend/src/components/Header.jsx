// The top bar: app title, the tab switcher (Devices / Keyboard), and the global
// demo-mode toggle (applies to whichever tab is active).
export default function Header({ active, onTab, demo, onToggleDemo }) {
  const tabs = [
    { id: "devices", label: "Devices" },
    { id: "keyboard", label: "Keyboard" },
  ];

  return (
    <header className="header">
      <h1>
        OS <span className="accent">Project</span>
      </h1>

      <nav className="tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            className={`tab ${active === t.id ? "active" : ""}`}
            onClick={() => onTab(t.id)}
            aria-current={active === t.id}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <button className="btn small" onClick={onToggleDemo}>
        {demo ? "Exit demo" : "Demo mode"}
      </button>
    </header>
  );
}
