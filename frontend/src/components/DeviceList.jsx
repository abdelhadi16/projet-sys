// The scrolling list of devices. Each entry is an expandable DeviceRow.
import DeviceRow from "./DeviceRow.jsx";

export default function DeviceList({ devices }) {
  if (devices.length === 0) {
    return <div className="empty">No devices match the current filter.</div>;
  }

  return (
    <div className="device-list">
      {devices.map((d) => (
        <DeviceRow key={d.instance_id} device={d} />
      ))}
    </div>
  );
}
