// A row of small stat cards summarising the current device list.
import { summarize } from "../lib/format.js";

export default function StatsBar({ devices }) {
  const s = summarize(devices);
  const cards = [
    { label: "Devices", value: s.total },
    { label: "Healthy", value: s.ok, tone: "ok" },
    { label: "Problems", value: s.problems, tone: s.problems ? "error" : "" },
    { label: "Classes", value: s.classes },
  ];

  return (
    <div className="stats">
      {cards.map((c) => (
        <div key={c.label} className={`stat ${c.tone || ""}`}>
          <div className="stat-value">{c.value}</div>
          <div className="stat-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}
