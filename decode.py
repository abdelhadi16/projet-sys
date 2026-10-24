"""
decode.py -- Module de décodage (Translateur : Decode + Context)
Objectif Transformer les RawEvents de Windows en DecodedEvent lisibles 
et récupérer le contexte de la fenêtre active pour le moteur de règles.
"""

from __future__ import annotations

import ctypes
import ntpath
import sys
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Optional

from task2pt1 import Context, DecodedEvent, EventType, Modifier, RawEvent

__all__ = ["decode", "get_context"]

# Gestion des erreurs propre sur stderr (sans jamais bloquer la callback)
_warned: set[str] = set()

def _warn(message: str) -> None:
    try:
        sys.stderr.write(f"[decode] {message}\n")
    except Exception:
        pass

def _warn_once(key: str, message: str) -> None:
    if key in _warned:
        return
    _warned.add(key)
    _warn(message)

# Chargement sécurisé des DLL Win32
_IS_WINDOWS = sys.platform == "win32"
_user32 = None
_kernel32 = None

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOUNICODE_NO_STATE_CHANGE = 0x4
_MAX_PATH_LONG = 32768

if _IS_WINDOWS:
    try:
        _user32 = ctypes.WinDLL("user32", use_last_error=True)
        _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        _user32.GetForegroundWindow.argtypes = []
        _user32.GetForegroundWindow.restype = wintypes.HWND

        _user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        _user32.GetWindowThreadProcessId.restype = wintypes.DWORD

        _user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        _user32.GetWindowTextLengthW.restype = ctypes.c_int

        _user32.GetWindowTextW.argtypes = [
            wintypes.HWND, ctypes.LPWSTR, ctypes.c_int]
        _user32.GetWindowTextW.restype = ctypes.c_int

        _user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
        _user32.GetKeyboardLayout.restype = ctypes.c_void_p

        _user32.ToUnicodeEx.argtypes = [
            wintypes.UINT, ctypes.UINT, ctypes.POINTER(ctypes.c_ubyte),
            wintypes.LPWSTR, ctypes.c_int, wintypes.UINT, ctypes.c_void_p]
        _user32.ToUnicodeEx.restype = ctypes.c_int

        _user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        _user32.GetAsyncKeyState.restype = ctypes.c_short

        _user32.GetKeyState.argtypes = [ctypes.c_int]
        _user32.GetKeyState.restype = ctypes.c_short

        _kernel32.OpenProcess.argtypes = [
            wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        _kernel32.OpenProcess.restype = wintypes.HANDLE

        _kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD)]
        _kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

        _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        _kernel32.CloseHandle.restype = wintypes.BOOL
    except Exception as exc:
        _user32 = None
        _kernel32 = None
        _warn(f"Impossible de charger les DLL Win32 : {exc!r}")


# Mappage des codes virtuels (vkCode) vers des noms humains clairs
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
    names: dict[int, str] = {}
    for vk in range(0x30, 0x3A):
        names[vk] = chr(vk)
    for vk in range(0x41, 0x5B):
        names[vk] = chr(vk)
    for i in range(10):
        names[0x60 + i] = f"NUM{i}"
    for i in range(24):
        names[0x70 + i] = f"F{i + 1}"
    names.update({
        0x08: "BACKSPACE", 0x09: "TAB", 0x0D: "ENTER", 0x13: "PAUSE",
        0x14: "CAPS_LOCK", 0x1B: "ESC", 0x20: "SPACE",
        0x21: "PAGE_UP", 0x22: "PAGE_DOWN", 0x23: "END", 0x24: "HOME",
        0x25: "LEFT", 0x26: "UP", 0x27: "RIGHT", 0x28: "DOWN",
        0x2C: "PRINT_SCREEN", 0x2D: "INSERT", 0x2E: "DELETE",
        0x5B: "LWIN", 0x5C: "RWIN", 0x5D: "APPS",
        0x6A: "NUM_MULTIPLY", 0x6B: "NUM_ADD", 0x6C: "NUM_SEPARATOR",
        0x6D: "NUM_SUBTRACT", 0x6E: "NUM_DECIMAL", 0x6F: "NUM_DIVIDE",
        0x90: "NUM_LOCK", 0x91: "SCROLL_LOCK",
        0x10: "SHIFT", 0x11: "CTRL", 0x12: "ALT",
        0xA0: "LSHIFT", 0xA1: "RSHIFT", 0xA2: "LCTRL", 0xA3: "RCTRL",
        0xA4: "LALT", 0xA5: "RALT",
        0xBA: "SEMICOLON", 0xBB: "EQUALS", 0xBC: "COMMA", 0xBD: "MINUS",
        0xBE: "PERIOD", 0xBF: "SLASH", 0xC0: "BACKTICK",
        0xDB: "LBRACKET", 0xDC: "BACKSLASH", 0xDD: "RBRACKET", 0xDE: "QUOTE",
        0xE2: "OEM_102", 0xE7: "PACKET",
    })
    return names


_KEY_NAMES = _build_key_names()

def _key_name(vk: int) -> str:
    return _KEY_NAMES.get(vk) or f"VK_0x{vk:02X}"


_PRINTABLE_VKS = frozenset(
    set(range(0x30, 0x3A)) | set(range(0x41, 0x5B)) | set(range(0x60, 0x6A))
    | {0x6A, 0x6B, 0x6D, 0x6E, 0x6F, VK_SPACE}
    | set(range(0xBA, 0xC1)) | set(range(0xDB, 0xE0)) | {0xE2}
)

_US_PLAIN = {
    VK_SPACE: " ", 0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".",
    0xBF: "/", 0xC0: "`", 0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
    0xE2: "\\", 0x6A: "*", 0x6B: "+", 0x6D: "-", 0x6E: ".", 0x6F: "/",
}
_US_SHIFTED = {
    0xBA: ":", 0xBB: "+", 0xBC: "<", 0xBD: "_", 0xBE: ">", 0xBF: "?",
    0xC0: "~", 0xDB: "{", 0xDC: "|", 0xDD: "}", 0xDE: '"', 0xE2: "|",
}
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


# Suivi de l'état des modificateurs (Shift, Ctrl, Alt, CapsLock)
@dataclass(slots=True)
class _Snapshot:
    shift: bool = False
    ctrl: bool = False
    alt: bool = False
    win: bool = False
    caps: bool = False
    altgr: bool = False

    def to_list(self) -> list[Modifier]:
        out: list[Modifier] = []
        if self.shift:
            out.append(Modifier.SHIFT)
        if self.ctrl:
            out.append(Modifier.CTRL)
        if self.alt:
            out.append(Modifier.ALT)
        if self.win:
            out.append(Modifier.WIN)
        if self.caps:
            out.append(Modifier.CAPS_LOCK)
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
        altgr = (VK_RMENU in h and VK_LCONTROL in h
                 and VK_RCONTROL not in h and VK_LMENU not in h)
        return _Snapshot(
            shift=bool(h & _SHIFT_VKS),
            ctrl=bool(h & _CTRL_VKS),
            alt=bool(h & _ALT_VKS),
            win=bool(h & _WIN_VKS),
            caps=self.caps_lock,
            altgr=altgr,
        )


_STATE = _ModifierState()
_LOCK = threading.Lock()


def _resync_modifiers() -> None:
    if _user32 is None:
        return
    try:
        with _LOCK:
            _STATE.held.clear()
            _STATE.down_keys.clear()
            for vk in _MODIFIER_VKS - {VK_SHIFT, VK_CONTROL, VK_MENU}:
                if _user32.GetAsyncKeyState(vk) & 0x8000:
                    _STATE.held.add(vk)
                    _STATE.down_keys.add(vk)
            _STATE.caps_lock = bool(_user32.GetKeyState(VK_CAPITAL) & 0x0001)
    except Exception as exc:
        _warn_once("resync", f"Erreur resync modificateurs : {exc!r}")


_resync_modifiers()


def _foreground_layout() -> Optional[int]:
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return None
        tid = _user32.GetWindowThreadProcessId(hwnd, None)
        return _user32.GetKeyboardLayout(tid) or None
    except Exception:
        return None


def _to_unicode(vk: int, scan: int, snap: _Snapshot) -> Optional[str]:
    if _user32 is None:
        return None
    try:
        keys = (ctypes.c_ubyte * 256)()
        if snap.shift:
            keys[VK_SHIFT] = 0x80
        if snap.ctrl:
            keys[VK_CONTROL] = 0x80
        if snap.alt:
            keys[VK_MENU] = 0x80
        if snap.caps:
            keys[VK_CAPITAL] = 0x01
        buf = ctypes.create_unicode_buffer(8)
        n = _user32.ToUnicodeEx(vk, scan, keys, buf, len(buf),
                              TOUNICODE_NO_STATE_CHANGE, _foreground_layout())
    except Exception as exc:
        _warn_once("tounicode", f"ToUnicodeEx a échoué : {exc!r}")
        return None
    return buf[:n] if n > 0 else ""


def _character_for(vk: int, scan: int, snap: _Snapshot) -> str:
    if vk == VK_PACKET:
        return chr(scan) if 0 < scan < 0x10000 and not 0xD800 <= scan <= 0xDFFF else ""
    if (snap.ctrl or snap.alt or snap.win) and not snap.altgr:
        return ""
    if vk == VK_RETURN:
        return "\n"
    if vk == VK_TAB:
        return "\t"
    if vk not in _PRINTABLE_VKS:
        return ""

    ch = _to_unicode(vk, scan, snap)
    if ch is None:
        ch = _us_character(vk, snap.shift, snap.caps)
    return ch


# Fonction principale 1 demandée : decode()
def decode(raw_event: RawEvent) -> DecodedEvent:
    try:
        vk = int(raw_event.key_code)
        is_press = raw_event.event_type == EventType.PRESS

        with _LOCK:
            _STATE.update(vk, is_press)
            snap = _STATE.snapshot()

        character = _character_for(vk, int(raw_event.scan_code), snap) if is_press else ""

        return DecodedEvent(
            raw=raw_event,
            key_name=_key_name(vk),
            character=character,
            modifiers=snap.to_list(),
        )
    except Exception as exc:
        _warn_once("decode", f"Erreur de décodage : {exc!r}")
        return DecodedEvent(raw=raw_event, key_name="VK_UNKNOWN", character="", modifiers=[])


def _window_title(hwnd) -> str:
    length = _user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    copied = _user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value if copied > 0 else ""


def _process_name(pid: int) -> str:
    now = time.monotonic()
    cached = _proc_cache.get(pid)
    if cached and cached[1] > now:
        return cached[0]

    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return "<unknown>"
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


_proc_cache: dict[int, tuple[str, float]] = {}


# Fonction principale 2 demandée : get_context()
def get_context() -> Context:
    if _user32 is None or _kernel32 is None:
        return Context(window_title="", process_name="", process_id=0)
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return Context(window_title="", process_name="", process_id=0)

        pid = wintypes.DWORD(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == 0:
            return Context(window_title=_window_title(hwnd), process_name="<unknown>", process_id=0)

        return Context(
            window_title=_window_title(hwnd),
            process_name=_process_name(pid.value),
            process_id=int(pid.value),
        )
    except Exception as exc:
        _warn_once("context", f"Erreur get_context : {exc!r}")
        return Context(window_title="", process_name="", process_id=0)