// The expanded view of a single device: every property Windows reported, shown
// as a key/value table. Used inside DeviceRow when a row is expanded.
import { formatValue } from "../lib/format.js";

// Fields we show first (the most useful ones), in this order. Any other fields
// present on the device are listed afterwards, alphabetically.
const PRIORITY_FIELDS = [
  "instance_id",
  "class_name",
  "class_guid",
  "manufacturer",
  "hardware_ids",
  "compatible_ids",
  "service",
  "driver_key",
  "status",
  "problem_code",
  "problem_description",
  "port_name",
  "enumerator_name",
  "container_id",
];

// Build the ordered list of [key, value] rows to display.
function orderedEntries(device) {
  const seen = new Set();
  const rows = [];
  for (const key of PRIORITY_FIELDS) {
    if (key in device) {
      rows.push([key, device[key]]);
      seen.add(key);
    }
  }
  // Remaining fields (e.g. friendly_name, description, bus info) after the
  // priority ones, sorted for stable output.
  for (const key of Object.keys(device).sort()) {
    if (!seen.has(key)) rows.push([key, device[key]]);
  }
  return rows;
}

export default function DeviceDetails({ device }) {
  return (
    <table className="details">
      <tbody>
        {orderedEntries(device).map(([key, value]) => (
          <tr key={key}>
            <th>{key}</th>
            <td>{formatValue(value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
