// ---------------------------------------------------------------------------
// Demo mode.
//
// The real backend (Kenza's FastAPI) streams the device list and pushes an
// updated list whenever a device is plugged or unplugged. Demo mode fakes that
// entirely in the browser so the UI can be shown WITHOUT any backend running:
// it starts from a snapshot of real devices (demo-devices.json, 175 entries
// captured from an actual machine) and periodically plugs/unplugs a fake USB
// stick so the live-update behaviour is visible.
//
// Kept in its own module (no React) so the hotplug logic is unit-testable.
// ---------------------------------------------------------------------------

import demoDevices from "../demo-devices.json";

// A fake removable device we toggle in and out to simulate hotplug.
const DEMO_USB = {
  friendly_name: "SanDisk Ultra USB 3.0 (Demo)",
  description: "USB Mass Storage Device",
  manufacturer: "SanDisk",
  class_name: "USB",
  class_guid: "{36fc9e60-c465-11cf-8056-444553540000}",
  hardware_ids: ["USB\\VID_0781&PID_5581", "USB\\VID_0781"],
  service: "USBSTOR",
  enumerator_name: "USB",
  is_present: true,
  instance_id: "USB\\VID_0781&PID_5581\\DEMO1234",
  status: "Ok",
  problem_code: 0,
  problem_description: null,
  port_name: null,
};

// A fresh copy of the starting device list (so callers can mutate safely).
export function demoInitialDevices() {
  return demoDevices.map((d) => ({ ...d }));
}

// Given the current list, return the next list with the demo USB toggled in or
// out. Pure function -> easy to test.
export function toggleDemoUsb(devices) {
  const present = devices.some((d) => d.instance_id === DEMO_USB.instance_id);
  if (present) {
    // Unplug it.
    return devices.filter((d) => d.instance_id !== DEMO_USB.instance_id);
  }
  // Plug it in (add to the front so it's easy to spot).
  return [{ ...DEMO_USB }, ...devices];
}

// Starts the hotplug simulation. Every `intervalMs` it toggles the demo USB and
// calls onUpdate(newList). Returns a stop() function. getList() lets us read the
// caller's current list so other changes (e.g. search) aren't clobbered.
export function startDemoHotplug(getList, onUpdate, intervalMs = 3000) {
  const id = setInterval(() => {
    onUpdate(toggleDemoUsb(getList()));
  }, intervalMs);
  return () => clearInterval(id);
}
