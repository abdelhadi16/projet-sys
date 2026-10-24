// ---------------------------------------------------------------------------
// Pure helpers for working with device objects. No React, no side effects, so
// they are easy to unit-test (see src/test/format.test.js).
//
// A "device" is one entry from GET /api/devices, i.e. DeviceInfo.to_dict() in
// task1ver2.py. Its properties (friendly_name, class_name, ...) are flattened
// onto the object alongside instance_id, status, problem_code, etc.
// ---------------------------------------------------------------------------

// Best human-readable name for a device, falling back through the fields that
// are most often filled in, and finally to the instance id.
export function deviceName(d) {
  return (
    d.friendly_name ||
    d.description ||
    d.instance_id ||
    "(unknown device)"
  );
}

// Device class, with a readable fallback when Windows didn't report one.
export function deviceClass(d) {
  return d.class_name || "(no class)";
}

// Map a status string to a CSS modifier used for the coloured badge.
// Statuses come from _get_devnode_status(): Ok / Disabled / Error / NotStarted.
export function statusClass(status) {
  switch (status) {
    case "Ok":
      return "ok";
    case "Disabled":
      return "disabled";
    case "Error":
      return "error";
    case "NotStarted":
      return "notstarted";
    default:
      return "unknown";
  }
}

// True when the device looks like a keyboard. Part 1 of the assignment ends by
// locating the keyboard, so we let the UI highlight it.
export function isKeyboard(d) {
  return (d.class_name || "").toLowerCase() === "keyboard";
}

// Turn any property value into a display string. Lists (hardware_ids, etc.)
// become comma-separated; booleans become Yes/No; null/undefined become "—".
export function formatValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

// The set of unique class names present, sorted, for the filter dropdown.
export function uniqueClasses(devices) {
  const set = new Set();
  for (const d of devices) set.add(deviceClass(d));
  return Array.from(set).sort((a, b) => a.localeCompare(b));
}

// Filter a device list by class name ("" = all) and a free-text search that
// matches the name, instance id, manufacturer or hardware ids.
export function filterDevices(devices, { classFilter = "", search = "" } = {}) {
  const q = search.trim().toLowerCase();
  return devices.filter((d) => {
    if (classFilter && deviceClass(d) !== classFilter) return false;
    if (!q) return true;
    const haystack = [
      deviceName(d),
      d.instance_id,
      d.manufacturer,
      ...(d.hardware_ids || []),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(q);
  });
}

// Small summary for the stats bar: totals and how many are healthy vs problem.
export function summarize(devices) {
  let ok = 0;
  let problems = 0;
  for (const d of devices) {
    if (d.status === "Ok") ok += 1;
    else problems += 1;
  }
  return {
    total: devices.length,
    ok,
    problems,
    classes: uniqueClasses(devices).length,
  };
}
