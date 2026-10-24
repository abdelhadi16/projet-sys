"""
run_server.py — entry point used to build the backend into a single .exe.

Why a separate file: when PyInstaller "freezes" the program there is no shell to
run `uvicorn main:app`, so we import the FastAPI `app` object directly and hand
it to uvicorn as an object (not the "main:app" import string). That avoids the
import machinery uvicorn would otherwise need inside the frozen exe.

Run the resulting exe inside the test VM. It enumerates devices, installs the
keyboard hook, and serves the dashboard API on port 8000 for every machine on
the network — so the React dashboard on your server can watch the VM live.

Run it as Administrator (the keyboard hook needs it).
"""

import os
import sys

import uvicorn

from main import app

if __name__ == "__main__":
    # Defaults: listen on every network interface (so your server can reach the
    # VM, not just localhost) on port 8000.
    host = os.environ.get("KBMONITOR_HOST", "0.0.0.0")
    port = int(os.environ.get("KBMONITOR_PORT", "8000"))

    # You can also set it at launch without rebuilding the exe:
    #   kbmonitor.exe 9000              -> port 9000
    #   kbmonitor.exe 0.0.0.0 9000      -> host + port
    args = sys.argv[1:]
    if len(args) == 1:
        port = int(args[0])
    elif len(args) >= 2:
        host, port = args[0], int(args[1])

    print(f"Serving dashboard API on http://{host}:{port}   (press Ctrl+C to stop)")
    uvicorn.run(app, host=host, port=port)
