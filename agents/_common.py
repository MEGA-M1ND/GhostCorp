"""
agents/_common.py — shared helpers for every SimCorp agent.

Centralizes the three things every agent needs:
  1. Robust JSON parsing with a guaranteed fallback (LLMs occasionally wrap
     JSON in prose or markdown fences — we never want a malformed response to
     crash a tick).
  2. A retry-wrapped async LLM call with exponential backoff (handles NVIDIA
     NIM 429 rate limits gracefully).
  3. Consistent agent activity logging into `state["agent_log"]`.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.state import SimCorpState


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict | None:
    """Best-effort extraction of a single JSON object from LLM output.

    Handles: raw JSON, ```json fenced blocks, and JSON embedded in prose.
    Returns None if nothing parseable is found.
    """
    if not text:
        return None

    # 1) Try a fenced code block first.
    fence = _FENCE_RE.search(text)
    candidates = []
    if fence:
        candidates.append(fence.group(1).strip())

    # 2) Try the substring between the first '{' and the last '}'.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    # 3) Try the whole thing.
    candidates.append(text.strip())

    for cand in candidates:
        try:
            parsed = json.loads(cand)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def parse_json(text: str, fallback: dict) -> dict:
    """extract_json() but always returns a dict (the fallback on failure)."""
    result = extract_json(text)
    return result if result is not None else dict(fallback)


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------

def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a value into [lo, hi]. Coerces non-numeric input to lo."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# LLM invocation with retry/backoff
# ---------------------------------------------------------------------------

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def ainvoke(llm: Any, system: str, user: str) -> str:
    """Invoke a chat model asynchronously and return its text content.

    Retries up to 3 times with exponential backoff (2s -> 4s -> 8s, capped at
    10s) which covers NVIDIA NIM 429 rate-limit responses. `reraise=True` means
    the final failure propagates so callers can apply their own fallback.
    """
    messages = [("system", system), ("human", user)]
    response = await llm.ainvoke(messages)
    # ChatNVIDIA returns an AIMessage; .content is the text body.
    return getattr(response, "content", str(response))


# ---------------------------------------------------------------------------
# Activity logging
# ---------------------------------------------------------------------------

def log_agent(state: SimCorpState, agent: str, action: str) -> None:
    """Append a structured entry to the dashboard activity feed (in place)."""
    state["agent_log"].append(
        {
            "agent": agent,
            "action": action,
            "quarter": state["quarter"],
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
