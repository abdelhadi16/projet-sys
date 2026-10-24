from __future__ import annotations

import ctypes
import json
import ntpath
import queue
import sys
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class EventType(str, Enum):
    PRESS = "PRESS"
    RELEASE = "RELEASE"


class VerdictAction(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    MODIFY = "MODIFY"
    INJECT = "INJECT"


class Modifier(str, Enum):
    SHIFT = "SHIFT"
    CTRL = "CTRL"
    ALT = "ALT"
    WIN = "WIN"
    CAPS_LOCK = "CAPS_LOCK"


@dataclass(slots=True)
class RawEvent:
    key_code: int
    scan_code: int
    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    is_injected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"key_code": self.key_code, "scan_code": self.scan_code, "event_type": self.event_type.value, "timestamp": self.timestamp, "is_injected": self.is_injected}


@dataclass(slots=True)
class DecodedEvent:
    raw: RawEvent
    key_name: str
    character: str
    modifiers: list[Modifier] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"raw": self.raw.to_dict(), "key_name": self.key_name, "character": self.character, "modifiers": [m.value for m in self.modifiers]}


@dataclass(slots=True)
class Context:
    window_title: str
    process_name: str
    process_id: int

    def to_dict(self) -> dict[str, Any]:
        return {"window_title": self.window_title, "process_name": self.process_name, "process_id": self.process_id}


@dataclass(slots=True)
class EnrichedEvent:
    decoded: DecodedEvent
    context: Context

    def to_dict(self) -> dict[str, Any]:
        return {"decoded": self.decoded.to_dict(), "context": self.context.to_dict()}


@dataclass(slots=True)
class Verdict:
    action: VerdictAction
    rule_id: Optional[str] = None
    replacement_key: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action.value, "rule_id": self.rule_id, "replacement_key": self.replacement_key}


@dataclass(slots=True)
class Rule:
    id: str
    enabled: bool = True
    priority: int = 0
    match_key: list[str] = field(default_factory=list)
    match_modifiers: list[Modifier] = field(default_factory=list)
    match_process: Optional[str] = None
    action: VerdictAction = VerdictAction.PASS
    replacement_key: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "enabled": self.enabled, "priority": self.priority, "match_key": self.match_key, "match_modifiers": [m.value for m in self.match_modifiers], "match_process": self.match_process, "action": self.action.value, "replacement_key": self.replacement_key}


@dataclass(slots=True)
class RuleStore:
    rules: list[Rule] = field(default_factory=list)
    observe_only: bool = False
    version: int = 1


@dataclass(slots=True)
class LogEntry:
    enriched_event: EnrichedEvent
    verdict: Verdict
    logged_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"enriched_event": self.enriched_event.to_dict(), "verdict": self.verdict.to_dict(), "logged_at": self.logged_at}


def decide_action(event: EnrichedEvent, store: RuleStore) -> Verdict:
    if store.observe_only:
        return Verdict(action=VerdictAction.PASS, rule_id="observe_only")
    sorted_rules = sorted(store.rules, key=lambda r: r.priority, reverse=True)
    for rule in sorted_rules:
        if not rule.enabled:
            continue
        if rule.match_key and event.decoded.key_name not in rule.match_key:
            continue
        if rule.match_process and event.context.process_name != rule.match_process:
            continue
        if rule.match_modifiers:
            event_mods = set(event.decoded.modifiers)
            required_mods = set(rule.match_modifiers)
            if not required_mods.issubset(event_mods):
                continue
        return Verdict(action=rule.action, rule_id=rule.id, replacement_key=rule.replacement_key)
    return Verdict(action=VerdictAction.PASS, rule_id=None)


event_queue: queue.Queue = queue.Queue(maxsize=10000)
_stop_event: Optional[threading.Event] = None
_flusher_thread: Optional[threading.Thread] = None
FALLBACK_FILE = Path("events_fallback.jsonl")


def push_event(q: queue.Queue, event: Any) -> None:
    if not isinstance(event, dict):
        if hasattr(event, "to_dict"):
            event = event.to_dict()
        else:
            return
    try:
        q.put_nowait(event)
    except queue.Full:
        try:
            q.get_nowait()
            q.put_nowait(event)
        except queue.Empty:
            pass


def _send_to_api(api_url: str, event: dict[str, Any]) -> bool:
    if not api_url:
        return False
    try:
        import urllib.request
        data = json.dumps(event, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(api_url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception:
        return False


def _write_fallback(event: dict[str, Any]) -> None:
    try:
        with open(FALLBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _flusher_worker(q: queue.Queue, api_url: str, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            event = q.get(timeout=0.5)
        except queue.Empty:
            continue
        success = _send_to_api(api_url, event)
        if not success:
            _write_fallback(event)
        q.task_done()


def start_flusher(q: queue.Queue, api_url: str = "") -> None:
    global _stop_event, _flusher_thread
    if _flusher_thread is not None and _flusher_thread.is_alive():
        return
    _stop_event = threading.Event()
    _flusher_thread = threading.Thread(target=_flusher_worker, args=(q, api_url, _stop_event), daemon=True, name="EventFlusher")
    _flusher_thread.start()


def stop_flusher(q: queue.Queue, timeout: float = 2.0) -> None:
    global _stop_event, _flusher_thread
    if _stop_event is None:
        return
    _stop_event.set()
    deadline = time.time() + timeout
    while not q.empty() and time.time() < deadline:
        time.sleep(0.05)
    if _flusher_thread is not None:
        _flusher_thread.join(timeout=1.0)
    _stop_event = None
    _flusher_thread = None


_IS_WINDOWS = sys.platform == "win32"
_user32 = ctypes.WinDLL("user32", use_last_error=True) if _IS_WINDOWS else None
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True) if _IS_WINDOWS else None

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOUNICODE_NO_STATE_CHANGE = 0x4
_MAX_PATH_LONG = 32768

if _IS_WINDOWS:
    _user32.GetForegroundWindow.argtypes = []
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    _user32.GetWindowTextLengthW.restype = ctypes.c_int
    _user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.GetWindowTextW.restype = ctypes.c_int
    _user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
    _user32.GetKeyboardLayout.restype = ctypes.c_void_p
    _user32.ToUnicodeEx.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_ubyte), wintypes.LPWSTR, ctypes.c_int, wintypes.UINT, ctypes.c_void_p]
    _user32.ToUnicodeEx.restype = ctypes.c_int
    _user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    _user32.GetAsyncKeyState.restype = ctypes.c_short
    _user32.GetKeyState.argtypes = [ctypes.c_int]
    _user32.GetKeyState.restype = ctypes.c_short
    _kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    _kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL


VK_BACK, VK_TAB, VK_RETURN = 0x08, 0x09, 0x0D
VK_SHIFT, VK_CONTROL, VK_MENU = 0x10, 0x11, 0x12
VK_CAPITAL = 0x14
VK_SPACE = 0x20
VK_LWIN, VK_RWIN = 0x5B, 0x5C
VK_LSHIFT, VK_RSHIFT = 0xA0, 0xA1
VK_LCONTROL, VK_RCONTROL = 0xA2, 0xA3
VK_LMENU, VK_RMENU = 0xA4, 0xA5
VK_PACKET = 0xE7

_SHIFT_VKS = frozenset({VK_SHIFT, VK_LSHIFT, VK_RSHIFT})
_CTRL_VKS = frozenset({VK_CONTROL, VK_LCONTROL, VK_RCONTROL})
_ALT_VKS = frozenset({VK_MENU, VK_LMENU, VK_RMENU})
_WIN_VKS = frozenset({VK_LWIN, VK_RWIN})
_MODIFIER_VKS = _SHIFT_VKS | _CTRL_VKS | _ALT_VKS | _WIN_VKS


def _build_key_names() -> dict[int, str]:
    names = {}
    for vk in range(0x30, 0x3A): names[vk] = chr(vk)
    for vk in range(0x41, 0x5B): names[vk] = chr(vk)
    for i in range(10): names[0x60 + i] = f"NUM{i}"
    for i in range(24): names[0x70 + i] = f"F{i + 1}"
    names.update({
        0x08: "BACKSPACE", 0x09: "TAB", 0x0D: "ENTER", 0x13: "PAUSE", 0x14: "CAPS_LOCK", 0x1B: "ESC", 0x20: "SPACE",
        0x21: "PAGE_UP", 0x22: "PAGE_DOWN", 0x23: "END", 0x24: "HOME", 0x25: "LEFT", 0x26: "UP", 0x27: "RIGHT", 0x28: "DOWN",
        0x2C: "PRINT_SCREEN", 0x2D: "INSERT", 0x2E: "DELETE", 0x5B: "LWIN", 0x5C: "RWIN", 0x5D: "APPS",
        0x6A: "NUM_MULTIPLY", 0x6B: "NUM_ADD", 0x6C: "NUM_SEPARATOR", 0x6D: "NUM_SUBTRACT", 0x6E: "NUM_DECIMAL", 0x6F: "NUM_DIVIDE",
        0x90: "NUM_LOCK", 0x91: "SCROLL_LOCK", 0x10: "SHIFT", 0x11: "CTRL", 0x12: "ALT",
        0xA0: "LSHIFT", 0xA1: "RSHIFT", 0xA2: "LCTRL", 0xA3: "RCTRL", 0xA4: "LALT", 0xA5: "RALT",
        0xBA: "SEMICOLON", 0xBB: "EQUALS", 0xBC: "COMMA", 0xBD: "MINUS", 0xBE: "PERIOD", 0xBF: "SLASH", 0xC0: "BACKTICK",
        0xDB: "LBRACKET", 0xDC: "BACKSLASH", 0xDD: "RBRACKET", 0xDE: "QUOTE", 0xE2: "OEM_102", 0xE7: "PACKET",
    })
    return names


_KEY_NAMES = _build_key_names()


def _key_name(vk: int) -> str:
    return _KEY_NAMES.get(vk) or f"VK_0x{vk:02X}"


_PRINTABLE_VKS = frozenset(set(range(0x30, 0x3A)) | set(range(0x41, 0x5B)) | set(range(0x60, 0x6A)) | {0x6A, 0x6B, 0x6D, 0x6E, 0x6F, VK_SPACE} | set(range(0xBA, 0xC1)) | set(range(0xDB, 0xE0)) | {0xE2})

_US_PLAIN = {VK_SPACE: " ", 0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".", 0xBF: "/", 0xC0: "`", 0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'", 0xE2: "\\", 0x6A: "*", 0x6B: "+", 0x6D: "-", 0x6E: ".", 0x6F: "/"}
_US_SHIFTED = {0xBA: ":", 0xBB: "+", 0xBC: "<", 0xBD: "_", 0xBE: ">", 0xBF: "?", 0xC0: "~", 0xDB: "{", 0xDC: "|", 0xDD: "}", 0xDE: '"', 0xE2: "|"}
_US_SHIFT_DIGITS = ")!@#$%^&*("


def _us_character(vk: int, shift: bool, caps: bool) -> str:
    if 0x41 <= vk <= 0x5A:
        ch = chr(vk)
        return ch if (shift ^ caps) else ch.lower()
    if 0x30 <= vk <= 0x39:
        return _US_SHIFT_DIGITS[vk - 0x30] if shift else chr(vk)
    if 0x60 <= vk <= 0x69:
        return str(vk - 0x60)
    if shift and vk in _US_SHIFTED:
        return _US_SHIFTED[vk]
    return _US_PLAIN.get(vk, "")


@dataclass(slots=True)
class _Snapshot:
    shift: bool = False
    ctrl: bool = False
    alt: bool = False
    win: bool = False
    caps: bool = False
    altgr: bool = False

    def to_list(self) -> list[Modifier]:
        out = []
        if self.shift: out.append(Modifier.SHIFT)
        if self.ctrl: out.append(Modifier.CTRL)
        if self.alt: out.append(Modifier.ALT)
        if self.win: out.append(Modifier.WIN)
        if self.caps: out.append(Modifier.CAPS_LOCK)
        return out


@dataclass(slots=True)
class _ModifierState:
    held: set[int] = field(default_factory=set)
    down_keys: set[int] = field(default_factory=set)
    caps_lock: bool = False

    def update(self, vk: int, is_press: bool) -> bool:
        if is_press:
            is_repeat = vk in self.down_keys
            self.down_keys.add(vk)
            if vk in _MODIFIER_VKS:
                self.held.add(vk)
            elif vk == VK_CAPITAL and not is_repeat:
                self.caps_lock = not self.caps_lock
            return is_repeat
        self.down_keys.discard(vk)
        self.held.discard(vk)
        return False

    def snapshot(self) -> _Snapshot:
        h = self.held
        altgr = (VK_RMENU in h and VK_LCONTROL in h and VK_RCONTROL not in h and VK_LMENU not in h)
        return _Snapshot(shift=bool(h & _SHIFT_VKS), ctrl=bool(h & _CTRL_VKS), alt=bool(h & _ALT_VKS), win=bool(h & _WIN_VKS), caps=self.caps_lock, altgr=altgr)


_STATE = _ModifierState()
_LOCK = threading.Lock()


def _resync_modifiers() -> None:
    if _user32 is None: return
    with _LOCK:
        _STATE.held.clear()
        _STATE.down_keys.clear()
        for vk in _MODIFIER_VKS - {VK_SHIFT, VK_CONTROL, VK_MENU}:
            if _user32.GetAsyncKeyState(vk) & 0x8000:
                _STATE.held.add(vk)
                _STATE.down_keys.add(vk)
        _STATE.caps_lock = bool(_user32.GetKeyState(VK_CAPITAL) & 0x0001)


_resync_modifiers()


def _foreground_layout() -> Optional[int]:
    hwnd = _user32.GetForegroundWindow()
    if not hwnd: return None
    tid = _user32.GetWindowThreadProcessId(hwnd, None)
    return _user32.GetKeyboardLayout(tid) or None


def _to_unicode(vk: int, scan: int, snap: _Snapshot) -> Optional[str]:
    if _user32 is None: return None
    keys = (ctypes.c_ubyte * 256)()
    if snap.shift: keys[VK_SHIFT] = 0x80
    if snap.ctrl: keys[VK_CONTROL] = 0x80
    if snap.alt: keys[VK_MENU] = 0x80
    if snap.caps: keys[VK_CAPITAL] = 0x01
    buf = ctypes.create_unicode_buffer(8)
    n = _user32.ToUnicodeEx(vk, scan, keys, buf, len(buf), TOUNICODE_NO_STATE_CHANGE, _foreground_layout())
    return buf[:n] if n > 0 else ""


def _character_for(vk: int, scan: int, snap: _Snapshot) -> str:
    if vk == VK_PACKET:
        return chr(scan) if 0 < scan < 0x10000 and not 0xD800 <= scan <= 0xDFFF else ""
    if (snap.ctrl or snap.alt or snap.win) and not snap.altgr:
        return ""
    if vk == VK_RETURN: return "\n"
    if vk == VK_TAB: return "\t"
    if vk not in _PRINTABLE_VKS: return ""
    ch = _to_unicode(vk, scan, snap)
    if ch is None: ch = _us_character(vk, snap.shift, snap.caps)
    return ch


_proc_cache: dict[int, tuple[str, float]] = {}
_PROC_CACHE_MAX = 100


def _window_title(hwnd) -> str:
    length = _user32.GetWindowTextLengthW(hwnd)
    if length <= 0: return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    copied = _user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value if copied > 0 else ""


def _process_name(pid: int) -> str:
    now = time.monotonic()
    cached = _proc_cache.get(pid)
    if cached and cached[1] > now:
        return cached[0]
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle: return "<unknown>"
    try:
        size = wintypes.DWORD(_MAX_PATH_LONG)
        buf = ctypes.create_unicode_buffer(_MAX_PATH_LONG)
        if not _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return "<unknown>"
        name = ntpath.basename(buf.value).lower() or "<unknown>"
    finally:
        _kernel32.CloseHandle(handle)
    if len(_proc_cache) >= _PROC_CACHE_MAX:
        _proc_cache.clear()
    _proc_cache[pid] = (name, now + 5.0)
    return name


def decode(raw_event: RawEvent) -> DecodedEvent:
    vk = int(raw_event.key_code)
    is_press = raw_event.event_type == EventType.PRESS
    with _LOCK:
        _STATE.update(vk, is_press)
        snap = _STATE.snapshot()
    character = _character_for(vk, int(raw_event.scan_code), snap) if is_press else ""
    return DecodedEvent(raw=raw_event, key_name=_key_name(vk), character=character, modifiers=snap.to_list())


def get_context() -> Context:
    if _user32 is None or _kernel32 is None: return Context(window_title="", process_name="", process_id=0)
    hwnd = _user32.GetForegroundWindow()
    if not hwnd: return Context(window_title="", process_name="", process_id=0)
    pid = wintypes.DWORD(0)
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == 0: return Context(window_title=_window_title(hwnd), process_name="<unknown>", process_id=0)
    return Context(window_title=_window_title(hwnd), process_name=_process_name(pid.value), process_id=int(pid.value))


WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
LLKHF_INJECTED = 0x10

install_hook = _user32.SetWindowsHookExW
LowLevelKeyboardProc = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
install_hook.argtypes = [ctypes.c_int, LowLevelKeyboardProc, wintypes.HMODULE, wintypes.DWORD]
install_hook.restype = wintypes.HHOOK
call_next_hook = _user32.CallNextHookEx
call_next_hook.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
call_next_hook.restype = ctypes.c_ssize_t
remove_hook = _user32.UnhookWindowsHookEx
remove_hook.argtypes = [wintypes.HHOOK]
remove_hook.restype = wintypes.BOOL
GetMessageW = _user32.GetMessageW
GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
GetMessageW.restype = wintypes.BOOL
TranslateMessage = _user32.TranslateMessage
TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
TranslateMessage.restype = wintypes.BOOL
DispatchMessageW = _user32.DispatchMessageW
DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
DispatchMessageW.restype = ctypes.c_ssize_t



class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD), ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


rule_store = RuleStore(observe_only=False)


@LowLevelKeyboardProc
def hook_proc(nCode, wParam, lParam):
    if nCode < 0:
        return call_next_hook(None, nCode, wParam, lParam)
    try:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        etype = EventType.PRESS if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN) else EventType.RELEASE
        raw_event = RawEvent(key_code=kb.vkCode, scan_code=kb.scanCode, event_type=etype, is_injected=bool(kb.flags & LLKHF_INJECTED))
        decoded_event = decode(raw_event)
        context = get_context()
        enriched_event = EnrichedEvent(decoded=decoded_event, context=context)
        verdict = decide_action(enriched_event, rule_store)
        log_entry = LogEntry(enriched_event=enriched_event, verdict=verdict)
        push_event(event_queue, log_entry)
        if verdict.action == VerdictAction.BLOCK:
            return 1
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
    return call_next_hook(None, nCode, wParam, lParam)


def main():
    start_flusher(event_queue, api_url="")
    hook = install_hook(WH_KEYBOARD_LL, hook_proc, None, 0)
    if not hook:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        msg = wintypes.MSG()
        while True:
            ret = GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == -1: raise ctypes.WinError(ctypes.get_last_error())
            if ret == 0: break
            TranslateMessage(ctypes.byref(msg))
            DispatchMessageW(ctypes.byref(msg))
    finally:
        stop_flusher(event_queue)
        remove_hook(hook)


if __name__ == "__main__":
    main()