// ---------------------------------------------------------------------------
// App — top level. Owns only the two cross-cutting choices: which tab is active
// and whether demo mode is on. Each tab's own state/logic lives in its view.
//
// Only the active view is mounted, so only its WebSocket runs at a time.
// ---------------------------------------------------------------------------

import { useState } from "react";

import Header from "./components/Header.jsx";
import DevicesView from "./views/DevicesView.jsx";
import KeyboardView from "./views/KeyboardView.jsx";

export default function App() {
  const [active, setActive] = useState("devices"); // "devices" | "keyboard"
  const [demo, setDemo] = useState(false);

  return (
    <div className="app">
      <Header
        active={active}
        onTab={setActive}
        demo={demo}
        onToggleDemo={() => setDemo((d) => !d)}
      />

      {active === "devices" ? (
        <DevicesView demo={demo} />
      ) : (
        <KeyboardView demo={demo} />
      )}
    </div>
  );
}
