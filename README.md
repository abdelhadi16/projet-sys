# Projet Système — Device Recognition & Control

University project (cybersecurity course). Two parts, on Windows:

1. **Device Recognition** — a program that enumerates every peripheral on the
   machine and prints its characteristics (name, class, hardware IDs, driver,
   status), reading Windows' own PnP database directly via `SetupAPI` / `CfgMgr`.
2. **Keyboard Control** — a system-wide low-level keyboard hook
   (`SetWindowsHookEx`, `WH_KEYBOARD_LL`) that intercepts every keystroke and can
   **log, block, or remap** keys according to user-defined rules.

A **FastAPI** backend exposes both over HTTP + WebSocket, and a **React** frontend
shows it all live in a browser.

## Repository layout

| File / folder | What it is | Member |
|---|---|---|
| `detectdevices.py` | Device enumerator (SetupAPI/CfgMgr) + hot-plug monitor | 1 |
| `takekbctrl.py` | Keyboard schemas + rules engine + decoder + hook + event pipe | 2–4 |
| `main.py` | FastAPI backend: device API + keyboard API (REST + WebSocket) | 1 |
| `frontend/` | React dashboard (2 tabs: Devices + Keyboard) | 5 |
| `devices.json` | Sample device enumeration output | — |

(`task1ver2.py`, `task2pt1.py`, `decode.py`, `hook.py`, `flusher.py` are the
earlier standalone modules that were merged into the files above.)

---

## How to run

You need **Python 3.11+** and **Node.js 18+**. Do this on the machine (or VM)
whose devices/keyboard you want to watch.

### 1. Backend (FastAPI)

```bash
pip install fastapi uvicorn pydantic
# Run as Administrator, so the keyboard hook can install:
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

On start it enumerates devices and installs the keyboard hook. The API is then at
`http://127.0.0.1:8000`.

### 2. Frontend (React)

```bash
cd frontend
npm install
npm run dev        # opens http://localhost:5173
```

Open http://localhost:5173 in a browser and switch tabs in the header.

> **No backend handy?** Click **Demo mode** (top-right). The UI runs on a real
> 175-device snapshot and fake keystrokes, so you can see everything work
> without running anything else.

---

## Standalone `.exe` + remote viewing (the realistic demo)

Package the backend into a single **`kbmonitor.exe`** that runs inside the test
VM, and watch it **live from another machine** ("the server"). Agent on one
machine, dashboard on another — the end-to-end demo the course asks for.

```
  [ VM ]  kbmonitor.exe  --(HTTP + WebSocket, port 8000)-->  [ Server ] dashboard
   hooks the keyboard,                                        React app in a browser
   serves the API                                             shows everything live
```

> Use this only on **your own VM / server** for the course demo. It is a
> visible tool (console window, unsigned, needs admin) — not hidden. Snapshot
> the VM first, in case a BLOCK rule locks the keyboard.

### 1. Build the exe
On a Windows machine with **Python 3.11+**, double-click **`build.bat`**. It
installs the dependencies and produces **`dist\kbmonitor.exe`** (needs no Python
on the machine you later run it on).

Manual equivalent:
```bash
pyinstaller --onefile --name kbmonitor --collect-all uvicorn run_server.py
```

### 2. Run it in the VM
Copy **`dist\kbmonitor.exe`** and **`run.bat`** into the VM, then double-click
**`run.bat`**. It asks for Administrator rights, opens the firewall for port
8000, prints the VM's IP, and starts the agent.

Manual: right-click `kbmonitor.exe` → **Run as administrator**. Change the port
without rebuilding with `kbmonitor.exe 9000` (or set `KBMONITOR_PORT`).

### 3. Watch from your server
Double-click **`run-dashboard.bat`**. It asks for the VM IP (the one `run.bat`
printed) and the port, installs the frontend the first time, and starts the
dashboard.

Manual equivalent:
```bash
cd frontend
# PowerShell — use the IP that run.bat printed:
$env:VITE_API_BASE = "http://192.168.1.50:8000"
npm run dev
```
Open <http://localhost:5173>. The **Devices** and **Keyboard** tabs now show the
VM live: type in the VM, see it on your server instantly; add a rule and switch
to **Blocking** to block/remap a key in the VM from your server.

Full details & troubleshooting: see **[BUILD_EXE.md](./BUILD_EXE.md)**.

---

## Mini test guide (for teammates)

**Where to run it:** run the **backend inside the VM** (and the frontend too, the
simplest setup). The hook captures keystrokes on the machine where `main.py`
runs, so you type in the VM and watch the dashboard there. Running in the VM also
means a bad BLOCK rule can't lock your real keyboard. **Take a VM snapshot
first.**

1. **Start** the backend (as Administrator) and the frontend as above.
2. **Devices tab**
   - You should see the full device list with stats at the top.
   - Use the search box / class filter — pick **Keyboard** to find the keyboard.
   - **Plug or unplug a USB device** → the list updates live within a second.
3. **Keyboard tab**
   - **Type anywhere** in the VM → events appear live (key, character, the
     focused app, and the verdict).
   - **Add a rule**: `+ Add rule` → id `block-win`, keys `LWIN, RWIN`, action
     `BLOCK`, Save.
   - Flip the switch from **Observe only** to **Blocking** → now press the
     Windows key: it is swallowed (Start menu won't open) and shows `BLOCK` in
     the feed. Flip back to **Observe only** to stop blocking.
4. **Connection dot** (top of each tab) should be green (**Connected**). If it's
   red, the backend isn't reachable — check it's running on port 8000.

### Running the frontend on your host instead of the VM (optional)

If you prefer the browser on your host machine pointing at the VM's backend, set
the backend address before `npm run dev`:

```bash
# PowerShell, replace with the VM's IP:
$env:VITE_API_BASE = "http://192.168.1.50:8000"
npm run dev
```

(and start uvicorn with `--host 0.0.0.0` so it accepts connections from outside
the VM, which the command above already does.)

### Automated tests (frontend)

```bash
cd frontend
npm test           # 46 unit + component + integration tests
```
