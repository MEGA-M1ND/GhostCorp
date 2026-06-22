"""
ghostcorp/agents/devops_agent.py — DevOps / Release. Nemotron-nano-8B.

Runs only after QA approves a green build. It bumps the product version, updates
the product manifest, writes a short release note, and commits the feature to the
product's git history — a real, versioned ship.
"""

from __future__ import annotations

import json

from ghostcorp import workspace as ws
from ghostcorp.agents._common import ainvoke, log_agent
from ghostcorp.llms import devops_llm
from ghostcorp.state import GhostCorpState

SYSTEM_PROMPT = (
    "You are the release engineer at GhostCorp. Write ONE punchy changelog line "
    "(max 12 words) for the shipped feature. No version number, no quotes, no prose."
)


def _bump_minor(version: str) -> str:
    try:
        parts = (version.split(".") + ["0", "0", "0"])[:3]
        major, minor = int(parts[0]), int(parts[1])
        return f"{major}.{minor + 1}.0"
    except (ValueError, IndexError):
        return "0.1.0"


async def devops_agent(state: GhostCorpState) -> GhostCorpState:
    state["status"] = "shipping"
    feature = state.get("current_feature", {})
    title = feature.get("title", "feature")

    new_version = _bump_minor(state["version"])
    state["version"] = new_version

    # Update the product manifest (drives the live preview header + /health).
    ws.write_file(
        "product.json",
        json.dumps(
            {"name": state["product_name"], "vision": state["product_vision"], "version": new_version},
            indent=2,
        )
        + "\n",
    )

    # Release note (LLM flourish; deterministic fallback).
    try:
        note = (await ainvoke(devops_llm, SYSTEM_PROMPT, f"Feature: {title}")).strip().splitlines()[0]
    except Exception:
        note = title
    note = note[:120] or title

    sha = ws.commit(f"Sprint {state['sprint']}: ship v{new_version} — {title}")

    # Refresh the code/history view for the dashboard.
    state["files"] = ws.list_files()
    state["commits"] = ws.git_log()
    state["last_diff"] = ws.last_commit_diff()

    state["changelog"].append(
        {
            "version": new_version,
            "sprint": state["sprint"],
            "title": title,
            "commit": sha,
            "summary": note,
        }
    )

    # Mark the backlog item shipped.
    for item in state["backlog"]:
        if item.get("id") == feature.get("id"):
            item["status"] = "shipped"
            break

    state["status"] = "idle"
    log_agent(state, "DevOps", f"shipped v{new_version} ({sha}) — {note}")
    return state
