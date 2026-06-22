"""
ghostcorp/agents/founder_agent.py — the Founder / CEO. Nemotron-70B.

The autonomy centerpiece: on the first sprint the CEO *invents the product* —
names it, writes the vision, and seeds a backlog of small, buildable features.
Each sprint it prioritizes the next feature (and replenishes the backlog when it
runs dry). The product and roadmap are the AI's own ideas.
"""

from __future__ import annotations

import json

from ghostcorp import workspace as ws
from ghostcorp.agents._common import ainvoke, log_agent, parse_json
from ghostcorp.llms import founder_llm
from ghostcorp.state import GhostCorpState

FOUND_SYSTEM = """You are the founder & CEO of GhostCorp, an AI-run software startup. Invent a SaaS product your engineering team can actually build as a FastAPI + SQLite web app.

HARD CONSTRAINTS on the product and its features:
- Every feature must be implementable as one or two simple REST endpoints (under /api/...) backed by SQLite.
- NO authentication, payments, external APIs, file uploads, or background jobs in the early backlog — keep features self-contained and testable.
- Start with core CRUD, then small enhancements (filtering, counts, status changes, search).

Output ONLY this JSON:
{
  "product_name": "short catchy name",
  "product_vision": "1-2 sentence vision",
  "backlog": [
    {"title": "Create X", "description": "what the endpoint(s) do"},
    ... 5 items, ordered by what to build first ...
  ]
}"""

IDEAS_SYSTEM = """You are the CEO of GhostCorp planning the next features for an existing product. Propose small, self-contained features, each buildable as one or two REST endpoints over SQLite (no auth/payments/external APIs). Output ONLY JSON:
{"backlog": [{"title": "...", "description": "..."}, ... 3 items ...]}"""

_FALLBACK_PRODUCT = {
    "product_name": "TaskFlow",
    "product_vision": "A minimal task-management SaaS for small teams.",
    "backlog": [
        {"title": "Create and list tasks", "description": "POST /api/tasks to create a task with a title; GET /api/tasks to list them."},
        {"title": "Complete a task", "description": "POST /api/tasks/{id}/complete marks a task done."},
        {"title": "Delete a task", "description": "DELETE /api/tasks/{id} removes a task."},
        {"title": "Filter tasks by status", "description": "GET /api/tasks?status=open|done filters the list."},
        {"title": "Task counts", "description": "GET /api/tasks/stats returns counts of open and done tasks."},
    ],
}


def _next_id(state: GhostCorpState) -> int:
    return max([i.get("id", 0) for i in state["backlog"]], default=0) + 1


def _add_items(state: GhostCorpState, items: list[dict]) -> None:
    for it in items:
        title = (it.get("title") or "").strip()
        if not title:
            continue
        state["backlog"].append(
            {
                "id": _next_id(state),
                "title": title,
                "description": (it.get("description") or "").strip(),
                "status": "pending",
            }
        )


def _write_product_json(state: GhostCorpState) -> None:
    ws.write_file(
        "product.json",
        json.dumps(
            {
                "name": state["product_name"],
                "vision": state["product_vision"],
                "version": state["version"],
            },
            indent=2,
        )
        + "\n",
    )


async def _found_company(state: GhostCorpState) -> None:
    try:
        raw = await ainvoke(founder_llm, FOUND_SYSTEM, "Found the company. Output JSON only.")
        data = parse_json(raw, _FALLBACK_PRODUCT)
    except Exception:
        data = dict(_FALLBACK_PRODUCT)

    state["product_name"] = (data.get("product_name") or _FALLBACK_PRODUCT["product_name"]).strip()
    state["product_vision"] = (data.get("product_vision") or _FALLBACK_PRODUCT["product_vision"]).strip()
    backlog = data.get("backlog") or _FALLBACK_PRODUCT["backlog"]
    _add_items(state, backlog)

    # Commit the product identity as its own commit so a failed first feature
    # (which reverts uncommitted work) can't erase the company's identity.
    _write_product_json(state)
    ws.commit(f"Sprint {state['sprint']}: found {state['product_name']}")
    state["files"] = ws.list_files()
    state["commits"] = ws.git_log()

    log_agent(
        state,
        "CEO",
        f"founded {state['product_name']} — \"{state['product_vision']}\" "
        f"with a {len(state['backlog'])}-feature backlog.",
    )


async def _replenish(state: GhostCorpState) -> None:
    shipped = [i["title"] for i in state["backlog"] if i["status"] == "shipped"]
    user = (
        f"Product: {state['product_name']} — {state['product_vision']}\n"
        f"Already shipped: {', '.join(shipped) if shipped else 'nothing yet'}\n"
        "Propose the next 3 features. JSON only."
    )
    try:
        data = parse_json(await ainvoke(founder_llm, IDEAS_SYSTEM, user), {"backlog": []})
    except Exception:
        data = {"backlog": []}
    items = data.get("backlog") or [
        {"title": "Search records", "description": "GET /api/search?q= returns matching records."}
    ]
    _add_items(state, items)
    log_agent(state, "CEO", f"added {len(items)} new feature(s) to the backlog.")


async def founder_agent(state: GhostCorpState) -> GhostCorpState:
    """Found the company (first sprint), then prioritize the next feature."""
    state["status"] = "planning"

    if not state["product_name"]:
        await _found_company(state)

    if not any(i["status"] == "pending" for i in state["backlog"]):
        await _replenish(state)

    pending = [i for i in state["backlog"] if i["status"] == "pending"]
    nxt = pending[0]
    state["current_feature"] = {
        "id": nxt["id"],
        "title": nxt["title"],
        "description": nxt["description"],
    }
    log_agent(state, "CEO", f"prioritized next feature: {nxt['title']}")
    return state
