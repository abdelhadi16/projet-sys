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

**Easiest — one click:** double-click **`build.bat`**. It installs what it needs
and produces `dist\kbmonitor.exe`. (First build takes a minute or two.)

**Or by hand:**

```bash
pip install pyinstaller fastapi uvicorn pydantic
pyinstaller --onefile --name kbmonitor --collect-all uvicorn run_server.py
```

- `--onefile` → a single `dist/kbmonitor.exe`.
- `--collect-all uvicorn` → bundles uvicorn's submodules (it loads some
  dynamically, so PyInstaller misses them without this). If launch fails with a
  `ModuleNotFoundError`, add the missing one, e.g. `--collect-all fastapi` or
  `--hidden-import=anyio`.

The exe appears at `dist/kbmonitor.exe`. It needs no Python on the target.

## 2. Set up and run it in the VM

1. **Copy** `dist\kbmonitor.exe` into the VM — put it in its own folder, e.g.
   `C:\kbmonitor\`.
2. **Run it as Administrator** — the keyboard hook needs it. Two ways:
   - Right-click `kbmonitor.exe` → **Run as administrator**, or
   - make a shortcut: right-click → *Create shortcut* → shortcut **Properties →
     Advanced… → Run as administrator** (so a double-click always elevates).

   A console window opens showing `Serving dashboard API on http://0.0.0.0:8000`.
3. **Pick a port (optional).** It defaults to **8000**. To change it without
   rebuilding, launch with an argument or an env var:
   ```cmd
   kbmonitor.exe 9000
   ```
   ```powershell
   $env:KBMONITOR_PORT = "9000"; .\kbmonitor.exe
   ```
4. **Allow it through the VM firewall** (match the port you chose):
   ```powershell
   New-NetFirewallRule -DisplayName "kbmonitor" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
   ```
5. Windows may warn it's an unsigned exe that uses a keyboard hook — expected for
   this kind of tool; allow it in your own test VM.
6. **Find the VM's IP:** run `ipconfig` → note the IPv4 address (e.g.
   `192.168.1.50`). Your server uses this next.

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
