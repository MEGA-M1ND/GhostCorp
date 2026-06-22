"""
ghostcorp/product_server.py — runs the AI-built product as a live subprocess.

The dashboard embeds the product in an iframe. We run it as its own uvicorn
process (rather than mounting it) so the product's root-relative routes
(`/health`, `/api/...`, `/`) resolve at their real paths. After each sprint the
process is restarted so the preview reflects newly shipped features.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request

from ghostcorp import workspace as ws


class ProductServer:
    def __init__(self) -> None:
        self.host = os.getenv("GHOSTCORP_PRODUCT_HOST", "127.0.0.1")
        self.port = int(os.getenv("GHOSTCORP_PRODUCT_PORT", "8100"))
        # The URL the browser uses for the iframe (may differ from bind host).
        self.public_url = os.getenv("GHOSTCORP_PREVIEW_URL", f"http://localhost:{self.port}")
        self._proc: subprocess.Popen | None = None

    @property
    def url(self) -> str:
        return self.public_url

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> bool:
        if self.is_running():
            return True
        if not ws.exists():
            return False
        self._proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app:app",
                "--host", self.host, "--port", str(self.port),
                "--log-level", "warning",
            ],
            cwd=str(ws.WORKSPACE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return self._wait_ready()

    def _wait_ready(self, timeout: float = 12.0) -> bool:
        deadline = time.time() + timeout
        url = f"http://{self.host}:{self.port}/health"
        while time.time() < deadline:
            if self._proc and self._proc.poll() is not None:
                return False  # process died (e.g. broken product) — give up
            try:
                with urllib.request.urlopen(url, timeout=1) as r:
                    if r.status == 200:
                        return True
            except Exception:
                time.sleep(0.2)
        return False

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def restart(self) -> bool:
        self.stop()
        return self.start()
