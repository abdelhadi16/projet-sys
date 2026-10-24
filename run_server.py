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

import uvicorn

from main import app

if __name__ == "__main__":
    # host="0.0.0.0" -> accept connections from other machines (your server),
    # not just localhost inside the VM.
    uvicorn.run(app, host="0.0.0.0", port=8000)
