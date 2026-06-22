"""
ghostcorp/state.py — GhostCorpState, the shared state for the AI software company.

One tick == one sprint. The state captures the company's identity (chosen by the
CEO), the backlog, the feature in flight, the real test verdict, the shipped
version history, and the live view of the codebase for the dashboard.
"""

from __future__ import annotations

from typing import List, TypedDict


class GhostCorpState(TypedDict):
    # --- Company / product identity (CEO sets these) ---
    sprint: int                     # Current sprint number (0 = seeded, not built)
    company: str                    # "GhostCorp"
    product_name: str               # Product the CEO chose to build
    product_vision: str             # One-paragraph vision
    status: str                     # "idle" | "planning" | "building" | "shipping" | "blocked"

    # --- Backlog & current work ---
    backlog: List[dict]             # [{id, title, description, priority, status}]
    current_feature: dict           # Feature being built this sprint (spec + criteria)

    # --- Shipping / versioning ---
    version: str                    # Product semver, e.g. "0.3.0"
    changelog: List[dict]           # [{version, sprint, title, commit, summary}]

    # --- Codebase view (for the dashboard) ---
    files: List[str]                # Current workspace file list
    last_diff: str                  # Latest code diff (what just shipped/attempted)
    commits: List[dict]             # [{sha, message}] product git history

    # --- Real QA verdict ---
    test_results: dict              # {passed, passed_count, failed_count, total, output, ...}
    build_attempts: int             # Engineer<->QA retries used this sprint

    # --- Activity + history ---
    agent_log: List[dict]           # [{agent, action, sprint, timestamp}]
    sprint_history: List[dict]      # Per-sprint snapshots for the timeline


def new_state(**overrides) -> GhostCorpState:
    """Build a fully-defaulted GhostCorpState (Sprint 0, no product chosen yet)."""
    base: GhostCorpState = {
        "sprint": 0,
        "company": "GhostCorp",
        "product_name": "",
        "product_vision": "",
        "status": "idle",
        "backlog": [],
        "current_feature": {},
        "version": "0.0.0",
        "changelog": [],
        "files": [],
        "last_diff": "",
        "commits": [],
        "test_results": {},
        "build_attempts": 0,
        "agent_log": [],
        "sprint_history": [],
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def sprint_snapshot(state: GhostCorpState) -> dict:
    """Compact per-sprint record for the dashboard timeline."""
    tr = state.get("test_results", {})
    return {
        "sprint": state["sprint"],
        "version": state["version"],
        "feature": state.get("current_feature", {}).get("title", ""),
        "tests_passed": tr.get("passed_count", 0),
        "tests_failed": tr.get("failed_count", 0),
        "shipped": bool(tr.get("passed")),
        "files": len(state.get("files", [])),
    }
