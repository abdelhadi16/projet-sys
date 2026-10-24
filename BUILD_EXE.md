# Building the `.exe` and watching the VM from your server

This turns the backend into one standalone `kbmonitor.exe` that runs in your test
VM, while the dashboard runs on your other machine ("the server") and shows the
VM's devices and keystrokes live over the network.

```
  [ VM ]  kbmonitor.exe  --(HTTP + WebSocket, port 8000)-->  [ Server ] dashboard
   hooks the keyboard,                                        React app in a browser
   serves the API                                             shows everything live
```

> Use this only on your own VM / server for the course demo. Keep a VM snapshot
> before running, in case a BLOCK rule locks the keyboard.

---

## 1. Build the exe (inside the VM, or any Windows box with Python)

```bash
pip install pyinstaller fastapi uvicorn pydantic

pyinstaller --onefile --name kbmonitor --collect-all uvicorn run_server.py
```

- `--onefile` → a single `dist/kbmonitor.exe`.
- `--collect-all uvicorn` → bundles uvicorn's submodules (it loads some
  dynamically, so PyInstaller misses them without this). If you still get a
  `ModuleNotFoundError` at launch, add the missing one, e.g.
  `--hidden-import=anyio` or `--collect-all fastapi`.

The exe appears at `dist/kbmonitor.exe`. It needs no Python on the target.

## 2. Run it in the VM

- Copy `dist/kbmonitor.exe` into the VM.
- **Run it as Administrator** (right-click → Run as administrator) — the keyboard
  hook needs it. A console window opens and prints "Starting Keyboard Hook…".
- Windows may warn that it's an unsigned exe that uses a keyboard hook — that is
  expected for this kind of tool; allow it in your own test VM.
- Open the VM's firewall for port 8000 so your server can reach it:
  ```powershell
  New-NetFirewallRule -DisplayName "kbmonitor" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
  ```
- Find the VM's IP: `ipconfig` → note the IPv4 address (e.g. `192.168.1.50`).

## 3. Watch from your server

On your server machine, run the dashboard and point it at the VM:

```bash
cd frontend
npm install
# PowerShell — use the VM's IP from step 2:
$env:VITE_API_BASE = "http://192.168.1.50:8000"
npm run dev
```

Open <http://localhost:5173>. Because the dashboard runs on `localhost:5173`
(already in the backend's allowed origins), it connects straight to the VM:

- **Devices tab** — the VM's hardware; plug/unplug a USB device in the VM → the
  list updates on your server within a second.
- **Keyboard tab** — **type anything in the VM** → it appears live on your
  server, with the key, character, the focused app, and the verdict. Add a rule
  and switch to **Blocking** to block/remap a key in the VM from your server.

That is the "real situation" demo: the agent runs on one machine, the console on
another sees everything as it happens.

---

### Notes
- If the connection dot stays red: the server can't reach the VM. Re-check the
  VM's IP, that the firewall rule is in place, and that the exe is running.
- To serve the dashboard from the VM instead (and browse it from the server at
  `http://<VM-IP>:5173`), run `npm run dev -- --host` and add
  `http://<VM-IP>:5173` to `allow_origins` in `main.py`.
- `kbmonitor.exe` also writes unsent events to `events_fallback.jsonl` next to it
  (that is the flusher's local backup when the API is unreachable).
