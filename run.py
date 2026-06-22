"""
run.py — one-command startup for GhostCorp.

    python run.py

Boots the FastAPI server (which serves both the REST API and the dashboard) and
opens the dashboard in your default browser. Reads configuration from .env.
"""

from __future__ import annotations

import os
import threading
import time
import webbrowser

from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("GHOSTCORP_HOST", "127.0.0.1")
PORT = int(os.getenv("GHOSTCORP_PORT", "8000"))
URL = f"http://{HOST}:{PORT}"


def _preflight() -> None:
    """Warn (don't fail) if the NVIDIA key is missing — the UI still loads."""
    if not os.getenv("NVIDIA_API_KEY"):
        print("\n  ⚠  NVIDIA_API_KEY is not set. The dashboard will load, but")
        print("     running a quarter needs a key. Copy .env.example -> .env")
        print("     and add your key from https://build.nvidia.com\n")
    else:
        print("\n  ✓  NVIDIA_API_KEY detected.")
    if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true" and os.getenv("LANGCHAIN_API_KEY"):
        print("  ✓  LangSmith tracing enabled "
              f"(project: {os.getenv('LANGCHAIN_PROJECT', 'ghostcorp-hackathon')}).\n")


def _open_browser() -> None:
    time.sleep(2)  # give uvicorn a moment to bind the port
    try:
        webbrowser.open(URL)
    except Exception:
        pass


def main() -> None:
    import uvicorn

    _preflight()
    print(f"  GhostCorp HQ  →  {URL}\n")
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run("api.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
