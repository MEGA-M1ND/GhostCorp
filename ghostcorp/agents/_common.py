"""
ghostcorp/agents/_common.py — shared helpers for the AI staff.

Reuses the generic JSON-parsing + retry-wrapped LLM call from the SimCorp
agents._common (they're domain-agnostic), and adds GhostCorp-specific helpers:
sprint-aware activity logging and a robust parser for the Engineer's file blocks.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

# Reuse the battle-tested generic helpers (retry/backoff LLM call + JSON parse).
from agents._common import ainvoke, clamp, extract_json, parse_json  # noqa: F401

from ghostcorp.state import GhostCorpState


def log_agent(state: GhostCorpState, agent: str, action: str) -> None:
    """Append a structured entry to the company activity feed (in place)."""
    state["agent_log"].append(
        {
            "agent": agent,
            "action": action,
            "sprint": state["sprint"],
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )


# --- Engineer file-block parsing -------------------------------------------
# The Engineer emits files as:
#   === FILE: features/foo.py ===
#   <content>
#   === END FILE ===
# which is far more robust for code than embedding it in JSON.
_FILE_BLOCK = re.compile(
    r"=== FILE:\s*(?P<path>.+?)\s*===\n(?P<body>.*?)\n=== END FILE ===",
    re.DOTALL,
)


def strip_code_fence(text: str) -> str:
    """Remove a wrapping ```lang ... ``` fence if the model added one."""
    s = text.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        lines = lines[1:]  # drop opening fence line
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines)
    return s.rstrip() + "\n"


def parse_file_blocks(text: str) -> list[dict]:
    """Extract [{path, content}] from the Engineer's output."""
    files = []
    for m in _FILE_BLOCK.finditer(text or ""):
        path = m.group("path").strip().lstrip("/")
        content = strip_code_fence(m.group("body"))
        if path:
            files.append({"path": path, "content": content})
    return files
