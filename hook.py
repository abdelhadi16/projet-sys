import task2pt1
import decode
import ctypes
from ctypes import wintypes
import sys
#* declaring the dll (dynamic link libraries) to use And Keywords
user32 = ctypes.WinDLL("user32", use_last_error = True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error = True)
WH_KEYBOARD_LL = 13
HC_ACTION      = 0
WM_KEYDOWN     = 0x0100
WM_KEYUP       = 0x0101
WM_SYSKEYDOWN  = 0x0104
WM_SYSKEYUP    = 0x0105
LLKHF_INJECTED = 0x10
#* defining native functions

#? some definitions bach ma tetlefch: 
# a Handle: An opaque token the OS gives you to access a kernel object 
#a Hook : A mechanism to intercept events , we register a callback (a HOOKPROC) that the OS calls before the event reaches its normal target.
# a Thread : a unit of execution that has : a thread ID, a thread handle(the access token to it), and a stack

install_hook = user32.SetWindowsHookExW
install_hook.argtypes = [ctypes.c_int, wintypes.HOOKPROC, wintypes.HMODULE, wintypes.DWORD ]
install_hook.restype = wintypes.HHOOK

call_next_hook = user32.CallNextHookEx
call_next_hook.argtypes = [
    wintypes.HHOOK,    
    ctypes.c_int,      
    wintypes.WPARAM,   
    wintypes.LPARAM,   
]
call_next_hook.restype = ctypes.c_ssize_t 

remove_hook = user32.UnhookWindowsHookEx
remove_hook.argtypes = [
    wintypes.HHOOK
]
remove_hook.restype = wintypes.BOOL

GetMessageW = user32.GetMessageW
GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),  
    wintypes.HWND,                 
    wintypes.UINT,                 
    wintypes.UINT,                 
]
GetMessageW.restype = wintypes.BOOL

TranslateMessage = user32.TranslateMessage
TranslateMessage.argtypes = [
    ctypes.POINTER(wintypes.MSG),   
]
TranslateMessage.restype = wintypes.BOOL

DispatchMessageW = user32.DispatchMessageW
DispatchMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),   
]
DispatchMessageW.restype = ctypes.c_ssize_t   

PostThreadMessageW = user32.PostThreadMessageW
PostThreadMessageW.argtypes = [
    wintypes.DWORD,    
    wintypes.UINT,     
    wintypes.WPARAM,   
    wintypes.LPARAM,   
]
PostThreadMessageW.restype = wintypes.BOOL

GetCurrentThreadId = kernel32.GetCurrentThreadId
GetCurrentThreadId.argtypes = []
GetCurrentThreadId.restype  = wintypes.DWORD

#* calling the Rules
rule_store = task2pt1.RuleStore(observe_only=True)


#* Defining the Callback

LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,      # LRESULT
    ctypes.c_int,          # nCode
    wintypes.WPARAM,       # wParam
    wintypes.LPARAM,       # lParam
)

#KBDLLHOOKSTRUCT : Contains information about a low-level keyboard input event.

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode",      wintypes.DWORD),
        ("scanCode",    wintypes.DWORD),
        ("flags",       wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t), 
    ]

#nCode: A code the hook procedure uses to determine how to process the message.
# If nCode is less than zero, the hook procedure must pass the message to the CallNextHookEx function without further processing and should return the value returned by CallNextHookEx.


@LowLevelKeyboardProc
def hook_proc(nCode, wParam, lParam):
    try:
        if nCode >= 0:
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            etype = (task2pt1.EventType.PRESS
                     if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                     else task2pt1.EventType.RELEASE)
            ev = task2pt1.RawEvent(
                key_code=kb.vkCode,
                scan_code=kb.scanCode,
                event_type=etype,
                is_injected=bool(kb.flags & LLKHF_INJECTED),
            )
            print(ev.to_dict())
            decoded_event = decode.decode(ev)
            context = decode.get_context()
            enriched_event = task2pt1.EnrichedEvent(
            decoded=decoded_event,
            context=context,
            )
            verdict = task2pt1.decide_action(
            enriched_event,
            rule_store
            )
            print("Event:", enriched_event.to_dict())
            print("Verdict:", verdict.to_dict())
    except Exception as e:
        sys.stderr.write(f'an Error occured : {e}')
    return call_next_hook(None, nCode, wParam, lParam)


def main():
    hook = install_hook(WH_KEYBOARD_LL, hook_proc, None, 0)
    if not hook:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        msg = wintypes.MSG()
        while True:
            ret = GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == -1:
                raise ctypes.WinError(ctypes.get_last_error())
            if ret == 0:
                break
            TranslateMessage(ctypes.byref(msg))
            DispatchMessageW(ctypes.byref(msg))
    finally:
        remove_hook(hook)

if __name__ == "__main__":
    main()