"""
ghostcorp/executor.py — the real code-execution engine.

This is the credibility anchor of GhostCorp: the QA agent's verdicts are backed
by *actually running pytest* in a subprocess against the product workspace, with
a timeout and captured output. Green/red is real, not a simulated score.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time

# Pytest summary-line fragments, e.g. "3 passed", "1 failed", "2 errors".
_PASS = re.compile(r"(\d+) passed")
_FAIL = re.compile(r"(\d+) failed")
_ERROR = re.compile(r"(\d+) error")


def run_command(cmd: list[str], cwd: str, timeout: int = 120) -> dict:
    """Run a subprocess safely with a timeout; never raises on failure."""
    start = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
            "duration": round(time.time() - start, 2),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": -1,
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + "\n[TIMEOUT]",
            "timed_out": True,
            "duration": round(time.time() - start, 2),
        }
    except Exception as exc:  # e.g. interpreter missing — surface, don't crash
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"[executor error] {exc}",
            "timed_out": False,
            "duration": round(time.time() - start, 2),
        }


def _count(pattern: re.Pattern, text: str) -> int:
    m = pattern.search(text)
    return int(m.group(1)) if m else 0


def run_tests(workspace_dir: str, timeout: int = 120) -> dict:
    """Run the product's pytest suite and return a structured verdict.

    `passed` is True only if pytest ran to completion with at least one passing
    test and zero failures/errors.
    """
    res = run_command(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=workspace_dir,
        timeout=timeout,
    )
    output = (res["stdout"] + "\n" + res["stderr"]).strip()

    passed_count = _count(_PASS, output)
    failed_count = _count(_FAIL, output)
    error_count = _count(_ERROR, output)

    passed = (
        not res["timed_out"]
        and failed_count == 0
        and error_count == 0
        and passed_count > 0
    )

    return {
        "passed": passed,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "error_count": error_count,
        "total": passed_count + failed_count + error_count,
        "timed_out": res["timed_out"],
        "duration": res["duration"],
        # Tail of the log — enough for the dashboard panel without flooding state.
        "output": output[-4000:],
    }


def syntax_check(workspace_dir: str, rel_path: str, timeout: int = 30) -> dict:
    """Compile a single Python file to catch syntax errors before running tests."""
    res = run_command(
        [sys.executable, "-m", "py_compile", rel_path], cwd=workspace_dir, timeout=timeout
    )
    ok = res["returncode"] == 0 and not res["timed_out"]
    return {"ok": ok, "output": (res["stdout"] + res["stderr"]).strip()[-2000:]}
