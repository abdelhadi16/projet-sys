// Search box + class filter dropdown. Controlled by the parent (App), so the
// current filter lives in one place and can be applied with filterDevices().
import { uniqueClasses } from "../lib/format.js";

export default function Toolbar({
  devices,
  classFilter,
  onClassFilter,
  search,
  onSearch,
  shown,
  total,
}) {
  const classes = uniqueClasses(devices);

  return (
    <div className="toolbar">
      <input
        type="text"
        className="search"
        placeholder="Search name, instance id, hardware id…"
        value={search}
        onChange={(e) => onSearch(e.target.value)}
        aria-label="Search devices"
      />

      <select
        value={classFilter}
        onChange={(e) => onClassFilter(e.target.value)}
        aria-label="Filter by device class"
      >
        <option value="">All classes</option>
        {classes.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      <span className="count">
        {shown} / {total}
      </span>
    </div>
  );
}
