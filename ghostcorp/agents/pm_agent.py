"""
ghostcorp/agents/pm_agent.py — the Product Manager. Nemotron-nano-8B.

Turns the CEO's chosen backlog item into a build-ready spec with concrete,
testable acceptance criteria that the Engineer (and QA) work against.
"""

from __future__ import annotations

from ghostcorp.agents._common import ainvoke, log_agent, parse_json
from ghostcorp.llms import pm_llm
from ghostcorp.state import GhostCorpState

SYSTEM_PROMPT = """You are a product manager at GhostCorp. Turn a feature idea into a precise, testable spec for a FastAPI + SQLite app. Acceptance criteria must be concrete (specific endpoints, methods, status codes, and JSON fields) so they can be unit-tested. Output ONLY JSON:
{
  "title": "concise feature title",
  "description": "1-2 sentences of what to build",
  "acceptance_criteria": ["GET /api/... returns ...", "POST /api/... with {...} creates ...", ...]
}"""


async def pm_agent(state: GhostCorpState) -> GhostCorpState:
    feature = state.get("current_feature", {})
    fallback = {
        "title": feature.get("title", "Feature"),
        "description": feature.get("description", ""),
        "acceptance_criteria": [
            f"Implement: {feature.get('description', feature.get('title', 'the feature'))}",
        ],
    }

    user = (
        f"Product: {state['product_name']} — {state['product_vision']}\n"
        f"Feature idea: {feature.get('title', '')} — {feature.get('description', '')}\n"
        "Write the spec. JSON only."
    )
    try:
        spec = parse_json(await ainvoke(pm_llm, SYSTEM_PROMPT, user), fallback)
    except Exception:
        spec = fallback

    criteria = spec.get("acceptance_criteria") or fallback["acceptance_criteria"]
    if not isinstance(criteria, list):
        criteria = [str(criteria)]

    # Enrich the in-flight feature (preserve id and the Engineer's _files marker).
    state["current_feature"].update(
        {
            "title": (spec.get("title") or feature.get("title", "Feature")).strip(),
            "description": (spec.get("description") or feature.get("description", "")).strip(),
            "acceptance_criteria": [str(c) for c in criteria][:6],
        }
    )

    log_agent(
        state,
        "PM",
        f"spec'd '{state['current_feature']['title']}' with "
        f"{len(state['current_feature']['acceptance_criteria'])} acceptance criteria.",
    )
    return state
