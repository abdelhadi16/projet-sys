from __future__ import annotations

import argparse
import ctypes
import datetime
import json
import sys
import threading
import winreg
from ctypes import wintypes
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Optional

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    def __str__(self) -> str:
        d4 = "".join(f"{b:02x}" for b in self.Data4)
        return f"{{{self.Data1:08x}-{self.Data2:04x}-{self.Data3:04x}-{d4[:4]}-{d4[4:]}}}"

    @classmethod
    def from_string(cls, text: str) -> "GUID":
        g = cls()
        _ole32.CLSIDFromString(wintypes.LPCWSTR(text), ctypes.byref(g))
        return g

class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("ClassGuid", GUID),
        ("DevInst", wintypes.DWORD),
        ("Reserved", ctypes.c_void_p),
    ]

class DEVPROPKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", wintypes.ULONG)]

    def __init__(self, fmtid: str, pid: int):
        super().__init__()
        self.fmtid = GUID.from_string(fmtid)
        self.pid = pid

_ole32 = ctypes.WinDLL("ole32.dll", use_last_error=True)
_ole32.CLSIDFromString.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(GUID)]
_ole32.CLSIDFromString.restype = ctypes.c_long

DIGCF_PRESENT = 0x00000002
DIGCF_ALLCLASSES = 0x00000004
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
ERROR_NO_MORE_ITEMS = 259
CR_SUCCESS = 0x00000000
DN_STARTED = 0x00000008
DN_HAS_PROBLEM = 0x00000400
CM_PROB_DISABLED = 22

DEVPROP_TYPE_UINT32 = 0x00000007
DEVPROP_TYPE_UINT64 = 0x00000009
DEVPROP_TYPE_GUID = 0x0000000D
DEVPROP_TYPE_FILETIME = 0x00000010
DEVPROP_TYPE_BOOLEAN = 0x00000011
DEVPROP_TYPE_STRING = 0x00000012
DEVPROP_TYPEMOD_LIST = 0x00002000
DEVPROP_TYPE_STRING_LIST = DEVPROP_TYPE_STRING | DEVPROP_TYPEMOD_LIST

_FMT_DEVICE = "{a45c254e-df1c-4efd-8020-67d146a850e0}"
_FMT_PRESENCE = "{540b947e-8b40-45bc-a8a2-6a0b894cbda2}"
_FMT_CONTAINER = "{8c7ed206-3f8a-4827-b3ab-ae9e1faefc6c}"

_DEVPKEY_DEFS: dict[str, tuple[str, int]] = {
    "friendly_name":   (_FMT_DEVICE, 14),
    "description":     (_FMT_DEVICE, 2),
    "manufacturer":    (_FMT_DEVICE, 13),
    "class_name":      (_FMT_DEVICE, 9),
    "class_guid":      (_FMT_DEVICE, 10),
    "hardware_ids":    (_FMT_DEVICE, 3),
    "compatible_ids":  (_FMT_DEVICE, 4),
    "service":         (_FMT_DEVICE, 6),
    "driver_key":      (_FMT_DEVICE, 11),
    "location_info":   (_FMT_DEVICE, 15),
    "location_paths":  (_FMT_DEVICE, 37),
    "pdo_name":        (_FMT_DEVICE, 16),
    "upper_filters":   (_FMT_DEVICE, 19),
    "lower_filters":   (_FMT_DEVICE, 20),
    "bus_type_guid":   (_FMT_DEVICE, 21),
    "bus_number":      (_FMT_DEVICE, 23),
    "address":         (_FMT_DEVICE, 30),
    "enumerator_name": (_FMT_DEVICE, 24),
    "removal_policy":  (_FMT_DEVICE, 33),
    "is_present":      (_FMT_PRESENCE, 5),
    "container_id":    (_FMT_CONTAINER, 2),
}

DEVPKEYS: dict[str, DEVPROPKEY] = {
    name: DEVPROPKEY(fmtid, pid) for name, (fmtid, pid) in _DEVPKEY_DEFS.items()
}

PROBLEM_CODE_DESCRIPTIONS: dict[int, str] = {
    0:  "No problem",
    1:  "Device is not configured correctly",
    3:  "Driver may be corrupted, or system is low on memory",
    10: "Device cannot start",
    12: "Device cannot find enough free resources to use",
    18: "Reinstall the drivers for this device",
    22: "Device is disabled",
    24: "Device is not present / not working / missing drivers",
    28: "Drivers for this device are not installed",
    31: "Windows cannot load the required drivers",
    39: "Windows cannot load the driver for this device",
    43: "Windows has stopped this device because it reported problems",
    45: "Device is not currently connected to the computer",
}

_setupapi = ctypes.WinDLL("setupapi.dll", use_last_error=True)
_cfgmgr32 = ctypes.WinDLL("cfgmgr32.dll", use_last_error=True)

_setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE
_setupapi.SetupDiGetClassDevsW.argtypes = [
    ctypes.POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD,
]

_setupapi.SetupDiEnumDeviceInfo.restype = wintypes.BOOL
_setupapi.SetupDiEnumDeviceInfo.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(SP_DEVINFO_DATA),
]

_setupapi.SetupDiGetDeviceInstanceIdW.restype = wintypes.BOOL
_setupapi.SetupDiGetDeviceInstanceIdW.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(SP_DEVINFO_DATA),
    wintypes.LPWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
]

_setupapi.SetupDiGetDevicePropertyW.restype = wintypes.BOOL
_setupapi.SetupDiGetDevicePropertyW.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(SP_DEVINFO_DATA), ctypes.POINTER(DEVPROPKEY),
    ctypes.POINTER(wintypes.ULONG), ctypes.POINTER(ctypes.c_ubyte), wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), wintypes.DWORD,
]

_setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL
_setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]

_cfgmgr32.CM_Get_DevNode_Status.restype = ctypes.c_uint32
_cfgmgr32.CM_Get_DevNode_Status.argtypes = [
    ctypes.POINTER(wintypes.ULONG), ctypes.POINTER(wintypes.ULONG),
    wintypes.DWORD, wintypes.ULONG,
]

CM_NOTIFY_FILTER_TYPE_DEVICEINSTANCE = 2
CM_NOTIFY_FILTER_FLAG_ALL_DEVICE_INSTANCES = 0x00000002
MAX_DEVICE_ID_LEN = 200

CM_NOTIFY_ACTION_DEVICEINSTANCEENUMERATED = 7
CM_NOTIFY_ACTION_DEVICEINSTANCESTARTED = 8
CM_NOTIFY_ACTION_DEVICEINSTANCEREMOVED = 9

_CM_NOTIFY_ACTION_NAMES: dict[int, str] = {
    CM_NOTIFY_ACTION_DEVICEINSTANCEENUMERATED: "Arrived",
    CM_NOTIFY_ACTION_DEVICEINSTANCESTARTED: "Started",
    CM_NOTIFY_ACTION_DEVICEINSTANCEREMOVED: "Removed",
}

class _CM_NOTIFY_FILTER(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("Flags", wintypes.DWORD),
        ("FilterType", wintypes.DWORD),
        ("Reserved", wintypes.DWORD),
        ("InstanceId", wintypes.WCHAR * MAX_DEVICE_ID_LEN),
    ]

_CM_NOTIFY_CALLBACK = ctypes.WINFUNCTYPE(
    wintypes.DWORD,
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_void_p,
    wintypes.DWORD,
)

_cfgmgr32.CM_Register_Notification.restype = ctypes.c_uint32
_cfgmgr32.CM_Register_Notification.argtypes = [
    ctypes.POINTER(_CM_NOTIFY_FILTER), ctypes.c_void_p,
    _CM_NOTIFY_CALLBACK, ctypes.POINTER(wintypes.HANDLE),
]
_cfgmgr32.CM_Unregister_Notification.restype = ctypes.c_uint32
_cfgmgr32.CM_Unregister_Notification.argtypes = [wintypes.HANDLE]

class DeviceMonitor:
    DEBOUNCE_SECONDS = 0.3

    def __init__(self, on_device_change: Callable[[list["DeviceInfo"]], None], present_only: bool = True) -> None:
        self._on_device_change = on_device_change
        self._present_only = present_only
        self._notify_handle = wintypes.HANDLE(0)
        self._callback_ref: Optional[Any] = None
        self._timer_lock = threading.Lock()
        self._debounce_timer: Optional[threading.Timer] = None

    def start(self) -> None:
        filt = _CM_NOTIFY_FILTER()
        filt.cbSize = ctypes.sizeof(_CM_NOTIFY_FILTER)
        filt.Flags = CM_NOTIFY_FILTER_FLAG_ALL_DEVICE_INSTANCES
        filt.FilterType = CM_NOTIFY_FILTER_TYPE_DEVICEINSTANCE
        self._callback_ref = _CM_NOTIFY_CALLBACK(self._raw_callback)
        cr = _cfgmgr32.CM_Register_Notification(
            ctypes.byref(filt), None, self._callback_ref, ctypes.byref(self._notify_handle)
        )
        if cr != CR_SUCCESS:
            raise OSError(f"CM_Register_Notification failed, CONFIGRET {cr}")

    def stop(self) -> None:
        with self._timer_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
                self._debounce_timer = None
        if self._notify_handle:
            _cfgmgr32.CM_Unregister_Notification(self._notify_handle)
            self._notify_handle = wintypes.HANDLE(0)

    def _raw_callback(self, h_notify, context, action, event_data, event_data_size) -> int:
        try:
            action_name = _CM_NOTIFY_ACTION_NAMES.get(action)
            if action_name is None:
                return CR_SUCCESS
            instance_id = None
            if event_data:
                instance_id = ctypes.wstring_at(event_data + 8)
            sys.stderr.write(f"[hotplug] {action_name}: {instance_id}\n")
            self._schedule_rescan()
        except Exception:
            pass
        return CR_SUCCESS

    def _schedule_rescan(self) -> None:
        with self._timer_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(self.DEBOUNCE_SECONDS, self._rescan)
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _rescan(self) -> None:
        try:
            devices = enumerate_devices(present_only=self._present_only)
        except OSError:
            return
        self._on_device_change(devices)

@dataclass(slots=True)
class DeviceInfo:
    instance_id: str
    properties: dict[str, Any] = field(default_factory=dict)
    status: str = "Unknown"
    problem_code: int = 0
    problem_description: Optional[str] = None
    port_name: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        flat = {**d.pop("properties"), **d}
        return flat

def _decode_string(buf: bytes) -> str:
    return buf.decode("utf-16-le", errors="ignore").rstrip("\x00")

def _decode_string_list(buf: bytes) -> list[str]:
    raw = buf.decode("utf-16-le", errors="ignore")
    return [s for s in raw.split("\x00") if s]

def _decode_uint32(buf: bytes) -> int:
    return int.from_bytes(buf[:4], "little", signed=False)

def _decode_uint64(buf: bytes) -> int:
    return int.from_bytes(buf[:8], "little", signed=False)

def _decode_boolean(buf: bytes) -> bool:
    return buf[0] != 0

def _decode_guid(buf: bytes) -> str:
    g = GUID.from_buffer_copy(buf[: ctypes.sizeof(GUID)])
    return str(g)

def _decode_filetime(buf: bytes) -> Optional[str]:
    low = int.from_bytes(buf[0:4], "little")
    high = int.from_bytes(buf[4:8], "little")
    ticks = (high << 32) | low
    if ticks == 0:
        return None
    unix_seconds = ticks / 10_000_000 - 11644473600
    try:
        dt = datetime.datetime.fromtimestamp(unix_seconds, tz=datetime.timezone.utc)
        return dt.isoformat()
    except (OverflowError, OSError, ValueError):
        return None

_DECODERS: dict[int, Callable[[bytes], Any]] = {
    DEVPROP_TYPE_STRING: _decode_string,
    DEVPROP_TYPE_STRING_LIST: _decode_string_list,
    DEVPROP_TYPE_UINT32: _decode_uint32,
    DEVPROP_TYPE_UINT64: _decode_uint64,
    DEVPROP_TYPE_BOOLEAN: _decode_boolean,
    DEVPROP_TYPE_GUID: _decode_guid,
    DEVPROP_TYPE_FILETIME: _decode_filetime,
}

def _get_device_instance_id(h_dev_info: int, devinfo: SP_DEVINFO_DATA) -> str:
    required = wintypes.DWORD(0)
    _setupapi.SetupDiGetDeviceInstanceIdW(
        h_dev_info, ctypes.byref(devinfo), None, 0, ctypes.byref(required)
    )
    if required.value == 0:
        return ""
    buf = ctypes.create_unicode_buffer(required.value)
    ok = _setupapi.SetupDiGetDeviceInstanceIdW(
        h_dev_info, ctypes.byref(devinfo), buf, required.value, None
    )
    return buf.value if ok else ""

def _read_property(h_dev_info: int, devinfo: SP_DEVINFO_DATA, key: DEVPROPKEY) -> Any:
    prop_type = wintypes.ULONG(0)
    required = wintypes.DWORD(0)
    _setupapi.SetupDiGetDevicePropertyW(
        h_dev_info, ctypes.byref(devinfo), ctypes.byref(key),
        ctypes.byref(prop_type), None, 0, ctypes.byref(required), 0,
    )
    if required.value == 0:
        return None
    buf = (ctypes.c_ubyte * required.value)()
    ok = _setupapi.SetupDiGetDevicePropertyW(
        h_dev_info, ctypes.byref(devinfo), ctypes.byref(key),
        ctypes.byref(prop_type), buf, required.value, None, 0,
    )
    if not ok:
        return None
    decoder = _DECODERS.get(prop_type.value)
    if decoder is None:
        return None
    return decoder(bytes(buf))

def _get_devnode_status(dev_inst: int) -> tuple[str, int]:
    status = wintypes.ULONG(0)
    problem = wintypes.ULONG(0)
    cr = _cfgmgr32.CM_Get_DevNode_Status(
        ctypes.byref(status), ctypes.byref(problem), dev_inst, 0
    )
    if cr != CR_SUCCESS:
        return "Unknown", 0
    if status.value & DN_HAS_PROBLEM:
        label = "Disabled" if problem.value == CM_PROB_DISABLED else "Error"
        return label, problem.value
    if not (status.value & DN_STARTED):
        return "NotStarted", 0
    return "Ok", 0

def get_port_name(instance_id: str) -> Optional[str]:
    key_path = rf"SYSTEM\CurrentControlSet\Enum\{instance_id}\Device Parameters"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "PortName")
            return str(value)
    except OSError:
        return None

def enumerate_devices(present_only: bool = True, include_port: bool = True) -> list[DeviceInfo]:
    flags = DIGCF_ALLCLASSES | (DIGCF_PRESENT if present_only else 0)
    h_dev_info = _setupapi.SetupDiGetClassDevsW(None, None, None, flags)
    if h_dev_info in (0, INVALID_HANDLE_VALUE):
        err = ctypes.get_last_error()
        raise OSError(f"SetupDiGetClassDevs failed, Win32 error {err}")
    devices: list[DeviceInfo] = []
    try:
        index = 0
        while True:
            devinfo = SP_DEVINFO_DATA()
            devinfo.cbSize = ctypes.sizeof(SP_DEVINFO_DATA)
            if not _setupapi.SetupDiEnumDeviceInfo(h_dev_info, index, ctypes.byref(devinfo)):
                err = ctypes.get_last_error()
                if err != ERROR_NO_MORE_ITEMS:
                    sys.stderr.write(f"[warn] enumeration stopped early, Win32 error {err}\n")
                break
            instance_id = _get_device_instance_id(h_dev_info, devinfo)
            if not instance_id:
                index += 1
                continue
            props = {
                name: _read_property(h_dev_info, devinfo, key)
                for name, key in DEVPKEYS.items()
            }
            props = {k: v for k, v in props.items() if v is not None}
            status, problem_code = _get_devnode_status(devinfo.DevInst)
            devices.append(DeviceInfo(
                instance_id=instance_id,
                properties=props,
                status=status,
                problem_code=problem_code,
                problem_description=PROBLEM_CODE_DESCRIPTIONS.get(problem_code) if problem_code else None,
                port_name=get_port_name(instance_id) if include_port else None,
            ))
            index += 1
    finally:
        _setupapi.SetupDiDestroyDeviceInfoList(h_dev_info)
    return devices

def main() -> None:
    parser = argparse.ArgumentParser(description="Enumerate Windows I/O devices via SetupAPI.")
    parser.add_argument("--all", action="store_true", help="include non-present (ghost) devices")
    parser.add_argument("--json", metavar="FILE", help="write full results as JSON to FILE")
    parser.add_argument("--class", dest="class_filter", help="filter by device class, e.g. Keyboard")
    parser.add_argument("--details", action="store_true", help="show all properties for each device")
    args = parser.parse_args()
    devices = enumerate_devices(present_only=not args.all)
    if args.class_filter:
        devices = [d for d in devices if d.properties.get("class_name") == args.class_filter]
    if args.details:
        print(f"{len(devices)} device(s) found\n")
        for d in devices:
            print("=" * 100)
            print(f"INSTANCE ID: {d.instance_id}")
            print(f"STATUS: {d.status}")
            print(f"PROBLEM CODE: {d.problem_code}")
            if d.problem_description:
                print(f"PROBLEM DESC: {d.problem_description}")
            if d.port_name:
                print(f"PORT NAME: {d.port_name}")
            print("-" * 100)
            if not d.properties:
                print("(no properties)")
            else:
                for key in sorted(d.properties):
                    value = d.properties[key]
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    print(f"{key}: {value}")
            print()
    else:
        print(f"{len(devices)} device(s) found\n")
        header = f"{'CLASS':<16} {'STATUS':<10} {'NAME':<45} INSTANCE ID"
        print(header)
        print("-" * len(header))
        for d in devices:
            cls = (d.properties.get("class_name") or "?")[:16]
            name = (d.properties.get("friendly_name") or d.properties.get("description") or "?")[:45]
            print(f"{cls:<16} {d.status:<10} {name:<45} {d.instance_id}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump([d.to_dict() for d in devices], f, indent=2, ensure_ascii=False)
        print(f"\nFull details written to {args.json}")

if __name__ == "__main__":
    main()