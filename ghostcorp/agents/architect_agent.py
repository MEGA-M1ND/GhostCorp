"""
ghostcorp/agents/architect_agent.py — the Architect. Nemotron-70B.

A MetaGPT-style design step that sits between the PM and the Engineer. Before any
code is written it defines the minimal data model (SQLite tables) and the exact
REST contract (endpoints, request/response shapes) that satisfies the feature's
acceptance criteria. The Engineer then implements *against this contract* and QA
tests against it — which makes codegen far more reliable than free-form writing.

The design is stored on `state['current_feature']['design']`. If the LLM is
unavailable the design is left empty and the Engineer falls back to building
straight from the acceptance criteria (pre-Architect behaviour).
"""

from __future__ import annotations

import re

from ghostcorp import workspace as ws
from ghostcorp.agents._common import ainvoke, log_agent, parse_json
from ghostcorp.llms import architect_llm
from ghostcorp.state import GhostCorpState

SYSTEM_PROMPT = """You are a software architect at GhostCorp. Design ONE feature for a FastAPI + SQLite app BEFORE any code is written. Produce the minimal data model and the exact REST contract that satisfies the acceptance criteria.

RULES:
- Endpoints live under /api/... and exchange JSON. Include only what this feature needs.
- Prefer reusing existing tables; create a new table only when necessary. Columns are SQL column definitions (e.g. "id INTEGER PRIMARY KEY AUTOINCREMENT", "title TEXT NOT NULL").
- No authentication, payments, file uploads, or external services.
- "module" is a short snake_case name -> the Engineer creates features/<module>.py.

Output ONLY this JSON:
{
  "module": "snake_case_name",
  "tables": [
    {"name": "table_name", "columns": ["id INTEGER PRIMARY KEY AUTOINCREMENT", "..."]}
  ],
  "endpoints": [
    {"method": "POST", "path": "/api/...", "request": {"field": "type"}, "response": {"field": "type"}, "description": "..."}
  ],
  "notes": "constraints the engineer must follow (status codes, validation, edge cases)"
}"""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")[:24] or "feature"


def _fallback_module(state: GhostCorpState) -> str:
    return _slug(state.get("current_feature", {}).get("title", "feature"))


async def architect_agent(state: GhostCorpState) -> GhostCorpState:
    feature = state.get("current_feature", {})
    criteria = feature.get("acceptance_criteria", [])
    existing = [
        f for f in ws.list_files()
        if f.startswith("features/") and f.endswith(".py") and f != "features/__init__.py"
    ]

    user = (
        f"Product: {state['product_name']} — {state['product_vision']}\n"
        f"Feature: {feature.get('title', '')} — {feature.get('description', '')}\n"
        f"Acceptance criteria:\n" + "\n".join(f"- {c}" for c in criteria) + "\n"
        f"Existing feature modules: {', '.join(existing) if existing else 'none'}\n"
        "Design the data model + REST contract. JSON only."
    )

    try:
        design = parse_json(await ainvoke(architect_llm, SYSTEM_PROMPT, user), {})
    except Exception:
        design = {}

    if not isinstance(design, dict) or not design.get("endpoints"):
        # Degrade gracefully: no contract -> Engineer builds from criteria alone.
        state["current_feature"]["design"] = {}
        log_agent(state, "Architect", "no design produced; engineer will build from the spec.")
        return state

    module = _slug(design.get("module") or _fallback_module(state))
    design["module"] = module
    design.setdefault("tables", [])
    design.setdefault("notes", "")

    state["current_feature"]["design"] = design
    state["current_feature"]["module"] = module

    log_agent(
        state,
        "Architect",
        f"designed {len(design.get('tables', []))} table(s) and "
        f"{len(design['endpoints'])} endpoint(s) for module '{module}'.",
    )
    return state
