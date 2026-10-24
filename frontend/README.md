# OS Project — Frontend (Member 5 · "The Face")

React dashboard for the project, with **two tabs** matching the two parts of the
assignment:

- **Devices** — every peripheral Windows knows about, as a **live list** that
  updates on plug/unplug, with search, a class filter (Keyboard, Mouse, USB,
  Net…), status badges, and an expandable details view per device. Keyboards are
  flagged, since locating the keyboard is the goal of Part 1.
- **Keyboard** — a **live key-event feed** (key, character, modifiers, focused
  app, verdict), a **rule editor** (block / remap keys, per-process, priority),
  and an **observe / blocking** mode switch.

Built with **Vite + React** (plain JavaScript + CSS, dark theme). No backend is
required to try it — use **Demo mode**.

## Requirements

- Node.js 18+ (ships with npm). Check: `node --version`

## Run it

```bash
cd frontend
npm install          # first time only
npm run dev          # starts the dev server at http://localhost:5173
```

Open http://localhost:5173 and switch tabs with the buttons in the header.

- **No backend yet?** Click **Demo mode** (top-right). Devices shows a real
  175-device snapshot with a simulated USB plug/unplug; Keyboard streams fake
  keystrokes through an in-memory rule store (edit rules and watch verdicts
  change).
- **Backend running?** Leave demo off. The app connects to
  `http://127.0.0.1:8000` (change in `src/config.js`): Devices uses
  `/api/devices` + `/ws/devices`; Keyboard uses `/api/rules` + `/ws/keyboard`.

## Run the tests

```bash
npm test             # runs all unit + component tests once (46 tests)
npm run test:watch   # re-runs on file changes
```

Tests cover the pure helpers (device + keyboard), the demo engines (device
hotplug, keyboard rule matching — which mirrors `decide_action()` in
`takekbctrl.py`), the components, and an App-level integration test of the tabs
and demo mode.

## Project layout

```
frontend/
  index.html
  src/
    config.js             # backend URL, WebSocket URLs, keyboard constants
    theme.css             # dark theme (all colours as CSS variables)
    main.jsx              # React entry point
    App.jsx               # tabs + demo toggle, mounts the active view
    demo-devices.json     # 175-device snapshot for Devices demo mode
    views/
      DevicesView.jsx     # Devices tab (list, stats, search, filter)
      KeyboardView.jsx    # Keyboard tab (feed, rules, mode switch)
    components/           # ConnectionStatus, StatsBar, Toolbar, DeviceList,
                          # DeviceRow, DeviceDetails, EventFeed, EventRow,
                          # ModeSwitch, RuleEditor, RuleForm, Header
    hooks/
      useDeviceSocket.js  # /ws/devices connection + reconnect + keepalive
      useKeyboardSocket.js# /ws/keyboard connection + reconnect + keepalive
    lib/
      api.js              # REST calls (devices + rules)
      format.js           # pure device helpers (unit-tested)
      keyboard.js         # pure keyboard helpers + demo rule engine (unit-tested)
      demo.js             # device demo snapshot + hotplug simulation
    test/                 # Vitest unit + component + integration tests
```

## The API it expects

See [API_CONTRACT.md](./API_CONTRACT.md) for the exact routes and WebSocket
message shapes for both tabs. They match `../main.py`, `../detectdevices.py`
(device shape) and `../takekbctrl.py` (rules + events).
