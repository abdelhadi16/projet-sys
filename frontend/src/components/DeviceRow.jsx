// One device in the list. Click it to expand and see the full property table.
// Shows: class badge, name, manufacturer, status badge. Keyboards are flagged
// because locating the keyboard is the goal of Part 1.
import { useState } from "react";
import DeviceDetails from "./DeviceDetails.jsx";
import { deviceName, deviceClass, statusClass, isKeyboard } from "../lib/format.js";

export default function DeviceRow({ device }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`device ${open ? "open" : ""}`}>
      <button
        type="button"
        className="device-head"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="device-class">{deviceClass(device)}</span>

        <span className="device-name">
          {deviceName(device)}
          {isKeyboard(device) && <span className="tag">keyboard</span>}
          <span className="device-sub">{device.manufacturer || device.instance_id}</span>
        </span>

        <span className={`badge ${statusClass(device.status)}`}>
          {device.status}
        </span>

        <span className="chevron">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="device-details">
          <DeviceDetails device={device} />
        </div>
      )}
    </div>
  );
}
