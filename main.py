from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio
import json
import queue
import uuid
import threading
from typing import Dict, List, Optional

import detectdevices
import takekbctrl as keyboard

device_update_queue = queue.Queue()
current_device_list: List[dict] = []
device_connections: Dict[str, WebSocket] = {}
keyboard_connections: Dict[str, WebSocket] = {}

class RuleInput(BaseModel):
    id: str
    enabled: bool
    priority: int
    match_key: List[str]
    match_modifiers: List[str]
    match_process: Optional[str] = None
    action: str
    replacement_key: Optional[int] = None

class RuleUpdatePayload(BaseModel):
    observe_only: bool
    rules: List[RuleInput]

def on_device_changed(new_devices: List[detectdevices.DeviceInfo]):
    global current_device_list
    devices_dict = [d.to_dict() for d in new_devices]
    current_device_list = devices_dict
    device_update_queue.put(devices_dict)

def start_device_monitor():
    monitor = detectdevices.DeviceMonitor(on_device_change=on_device_changed, present_only=True)
    monitor.start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global current_device_list
    
    print("Starting Device Monitor...")
    initial_devices = detectdevices.enumerate_devices(present_only=True)
    current_device_list = [d.to_dict() for d in initial_devices]
    threading.Thread(target=start_device_monitor, daemon=True).start()
    
    print("Starting Keyboard Hook...")
    keyboard.start_flusher(keyboard.event_queue, api_url="")
    hook_thread = threading.Thread(target=keyboard.main, daemon=True)
    hook_thread.start()
    
    # Keep strong references to the background tasks. asyncio only holds a weak
    # reference, so without these variables the garbage collector can kill the
    # loops mid-run and live updates would silently stop.
    device_task = asyncio.create_task(process_device_updates())
    keyboard_task = asyncio.create_task(process_keyboard_events())
    
    yield
    
    print("Shutting down...")
    # Stop the background loops cleanly before exiting.
    device_task.cancel()
    keyboard_task.cancel()
    await asyncio.gather(device_task, keyboard_task, return_exceptions=True)
    keyboard.stop_flusher(keyboard.event_queue)

app = FastAPI(title="OS Project API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def process_device_updates():
    while True:
        try:
            updated = device_update_queue.get_nowait()
            message = json.dumps({"type": "DEVICE_UPDATE", "devices": updated})
            disconnected = []
            for sid, ws in device_connections.items():
                try: await ws.send_text(message)
                except: disconnected.append(sid)
            for sid in disconnected: device_connections.pop(sid, None)
        except queue.Empty:
            pass
        await asyncio.sleep(0.1)

async def process_keyboard_events():
    while True:
        try:
            event_data = keyboard.event_queue.get_nowait()
            message = json.dumps({"type": "KEY_EVENT", "data": event_data})
            disconnected = []
            for sid, ws in keyboard_connections.items():
                try: await ws.send_text(message)
                except: disconnected.append(sid)
            for sid in disconnected: keyboard_connections.pop(sid, None)
        except queue.Empty:
            pass
        await asyncio.sleep(0.05)

@app.get("/api/devices")
def get_devices(class_filter: Optional[str] = None):
    if class_filter:
        filtered = [d for d in current_device_list if d.get("class_name", "").lower() == class_filter.lower()]
        return JSONResponse(content={"count": len(filtered), "devices": filtered}, media_type="application/json; charset=utf-8")
    return JSONResponse(content={"count": len(current_device_list), "devices": current_device_list}, media_type="application/json; charset=utf-8")

@app.get("/api/devices/{instance_id}")
def get_device(instance_id: str):
    for d in current_device_list:
        if d.get("instance_id") == instance_id:
            return JSONResponse(content=d, media_type="application/json; charset=utf-8")
    raise HTTPException(status_code=404, detail="Device not found")

@app.websocket("/ws/devices")
async def ws_devices(websocket: WebSocket):
    await websocket.accept()
    sid = str(uuid.uuid4())
    device_connections[sid] = websocket
    try:
        await websocket.send_text(json.dumps({"type": "INITIAL_STATE", "devices": current_device_list}))
        while True:
            data = await websocket.receive_text()
            if data == "ping": await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        device_connections.pop(sid, None)
    except Exception:
        device_connections.pop(sid, None)

@app.get("/api/rules")
def get_rules():
    return {"observe_only": keyboard.rule_store.observe_only, "version": keyboard.rule_store.version, "rules": [r.to_dict() for r in keyboard.rule_store.rules]}

@app.post("/api/rules")
def update_rules(payload: RuleUpdatePayload):
    new_rules = []
    for r in payload.rules:
        new_rules.append(keyboard.Rule(
            id=r.id, enabled=r.enabled, priority=r.priority, match_key=r.match_key,
            match_modifiers=r.match_modifiers, match_process=r.match_process,
            action=r.action, replacement_key=r.replacement_key
        ))
    new_store = keyboard.RuleStore(rules=new_rules, observe_only=payload.observe_only, version=keyboard.rule_store.version + 1)
    keyboard.rule_store = new_store
    return {"status": "success", "version": keyboard.rule_store.version}

@app.websocket("/ws/keyboard")
async def ws_keyboard(websocket: WebSocket):
    await websocket.accept()
    sid = str(uuid.uuid4())
    keyboard_connections[sid] = websocket
    try:
        await websocket.send_text(json.dumps({"type": "INITIAL_STATE", "rules": [r.to_dict() for r in keyboard.rule_store.rules], "observe_only": keyboard.rule_store.observe_only}))
        while True:
            data = await websocket.receive_text()
            if data == "ping": await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        keyboard_connections.pop(sid, None)
    except Exception:
        keyboard_connections.pop(sid, None)