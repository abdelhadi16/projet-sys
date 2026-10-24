# API contract — frontend ⇄ backend

What the React frontend (Member 5) consumes from the FastAPI backend
(Member 1 / Kenza, `../main.py`). `main.py` serves **two** APIs — devices and
keyboard — and the frontend has one tab for each.

Base URL (dev): `http://127.0.0.1:8000` — change in `src/config.js` if needed.
CORS already allows the dev origin `http://localhost:5173` (set in `main.py`).

---

## Devices tab

Device shape = `DeviceInfo.to_dict()` in `../detectdevices.py`: the device's
properties flattened onto the object alongside `instance_id`, `status`,
`problem_code`, `problem_description`, `port_name`. `status` is one of
`Ok` / `Disabled` / `Error` / `NotStarted` / `Unknown`.

| Method | Path                         | Response                                |
|--------|------------------------------|-----------------------------------------|
| GET    | `/api/devices`               | `{ count, devices: [Device] }`          |
| GET    | `/api/devices?class_filter=Keyboard` | same, filtered by class server-side |
| GET    | `/api/devices/{instance_id}` | one `Device`, or `404`                  |

WebSocket `/ws/devices` — every message carries the **full** device list:
- on connect: `{ "type": "INITIAL_STATE", "devices": [Device] }`
- on change:  `{ "type": "DEVICE_UPDATE", "devices": [Device] }`
- keepalive: client sends `ping`, server replies `{ "type": "pong" }`

---

## Keyboard tab

Rule shape = `Rule.to_dict()` in `../takekbctrl.py`:

```json
{
  "id": "block-win-key",
  "enabled": true,
  "priority": 10,
  "match_key": ["LWIN", "RWIN"],
  "match_modifiers": [],
  "match_process": null,
  "action": "BLOCK",
  "replacement_key": null
}
```
- `action`: `PASS` | `BLOCK` | `MODIFY` | `INJECT`
- `match_modifiers` items: `SHIFT` | `CTRL` | `ALT` | `WIN` | `CAPS_LOCK`

| Method | Path          | Body                              | Response                         |
|--------|---------------|-----------------------------------|----------------------------------|
| GET    | `/api/rules`  | —                                 | `{ observe_only, version, rules: [Rule] }` |
| POST   | `/api/rules`  | `{ observe_only, rules: [Rule] }` | `{ status, version }`            |

> **Note:** there are no per-rule routes and no separate mode route. `POST
> /api/rules` **replaces the whole store**, so every change (add / edit /
> delete / enable / disable / toggle observe-only) sends the full
> `{ observe_only, rules }`.

WebSocket `/ws/keyboard`:
- on connect: `{ "type": "INITIAL_STATE", "rules": [Rule], "observe_only": bool }`
- per keystroke: `{ "type": "KEY_EVENT", "data": <LogEntry> }`
- keepalive: client sends `ping`, server replies `{ "type": "pong" }`

`LogEntry` (`takekbctrl.LogEntry.to_dict()`):

```json
{
  "enriched_event": {
    "decoded": {
      "raw": { "key_code": 65, "scan_code": 30, "event_type": "PRESS", "timestamp": 1730000000.1, "is_injected": false },
      "key_name": "A",
      "character": "a",
      "modifiers": ["SHIFT"]
    },
    "context": { "window_title": "Notepad", "process_name": "notepad.exe", "process_id": 4821 }
  },
  "verdict": { "action": "PASS", "rule_id": null, "replacement_key": null },
  "logged_at": 1730000000.1
}
```
