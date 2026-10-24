// ---------------------------------------------------------------------------
// DevicesView — the Devices tab. Shows the live device list with stats, search
// and a class filter. Talks to the device API, or runs on a real snapshot +
// simulated hotplug when `demo` is true.
// ---------------------------------------------------------------------------

import { useEffect, useMemo, useRef, useState } from "react";

import ConnectionStatus from "../components/ConnectionStatus.jsx";
import StatsBar from "../components/StatsBar.jsx";
import Toolbar from "../components/Toolbar.jsx";
import DeviceList from "../components/DeviceList.jsx";

import { useDeviceSocket } from "../hooks/useDeviceSocket.js";
import * as api from "../lib/api.js";
import { demoInitialDevices, startDemoHotplug } from "../lib/demo.js";
import { filterDevices } from "../lib/format.js";

export default function DevicesView({ demo }) {
  const [devices, setDevices] = useState([]);
  const [classFilter, setClassFilter] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState(null);

  // Live device list over the WebSocket (idle while demo mode is on).
  const status = useDeviceSocket({
    enabled: !demo,
    onDevices: (list) => {
      setDevices(list);
      setError(null);
    },
  });

  // One REST fetch on connect so the list shows even before INITIAL_STATE.
  useEffect(() => {
    if (demo) return;
    api
      .getDevices()
      .then((data) => {
        setDevices(data.devices || []);
        setError(null);
      })
      .catch(() =>
        setError("Backend not reachable. Turn on Demo mode to preview the UI.")
      );
  }, [demo]);

  // Demo mode: real snapshot + simulated USB hotplug.
  const devicesRef = useRef(devices);
  devicesRef.current = devices;
  useEffect(() => {
    if (!demo) return;
    setDevices(demoInitialDevices());
    setError(null);
    return startDemoHotplug(() => devicesRef.current, setDevices);
  }, [demo]);

  // Filter 175 devices only when the inputs actually change.
  const shown = useMemo(
    () => filterDevices(devices, { classFilter, search }),
    [devices, classFilter, search]
  );

  return (
    <>
      <div className="subbar">
        <ConnectionStatus status={status} demo={demo} />
      </div>

      {error && !demo && <div className="banner">{error}</div>}

      <StatsBar devices={devices} />

      <section className="panel">
        <Toolbar
          devices={devices}
          classFilter={classFilter}
          onClassFilter={setClassFilter}
          search={search}
          onSearch={setSearch}
          shown={shown.length}
          total={devices.length}
        />
        <DeviceList devices={shown} />
      </section>
    </>
  );
}
