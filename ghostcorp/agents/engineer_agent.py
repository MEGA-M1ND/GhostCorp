"""
ghostcorp/agents/engineer_agent.py — the Engineer. Nemotron-70B.

Implements ONE feature per call as a self-contained feature module plus a pytest
test file, writing real files into the product workspace. On a retry it receives
the failing test output and the current file contents so it can fix the code.
"""

from __future__ import annotations

from ghostcorp import workspace as ws
from ghostcorp.agents._common import ainvoke, log_agent, parse_file_blocks
from ghostcorp.llms import engineer_llm
from ghostcorp.state import GhostCorpState

# The Engineer may only write within these areas of the product.
_ALLOWED_PREFIXES = ("features/", "tests/", "templates/", "static/")
_ALLOWED_FILES = {"app.py", "db.py"}

SYSTEM_PROMPT = """You are a senior software engineer at GhostCorp building a FastAPI + SQLite SaaS product. You implement exactly ONE feature as a self-contained module plus tests.

ARCHITECTURE & CONVENTIONS (follow EXACTLY):
- The app auto-discovers modules in features/. Create features/<name>.py that defines `router = APIRouter()`. NEVER edit app.py.
- API endpoints live under /api/... and return JSON. Use pydantic BaseModel for request bodies.
- Persistence: `from db import connect`. Create tables with `CREATE TABLE IF NOT EXISTS` at import time.
- Write tests/test_<name>.py using fastapi.testclient. EVERY test file MUST start with exactly:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from fastapi.testclient import TestClient
    from app import app
    client = TestClient(app)
- Tests must be independent and must not assume an empty database (use unique values). Cover the acceptance criteria with real assertions.
- Write COMPLETE, runnable files. No placeholders, no TODOs, no prose outside file blocks.

OUTPUT FORMAT — output ONLY file blocks, nothing before or after:
=== FILE: features/<name>.py ===
<full file content>
=== END FILE ===
=== FILE: tests/test_<name>.py ===
<full file content>
=== END FILE ===

EXAMPLE:
=== FILE: features/ping.py ===
from fastapi import APIRouter
router = APIRouter()

@router.get("/api/ping")
def ping():
    return {"pong": True}
=== END FILE ===
=== FILE: tests/test_ping.py ===
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from app import app
client = TestClient(app)

def test_ping():
    r = client.get("/api/ping")
    assert r.status_code == 200
    assert r.json()["pong"] is True
=== END FILE ==="""


def _allowed(path: str) -> bool:
    return path in _ALLOWED_FILES or path.startswith(_ALLOWED_PREFIXES)


def _design_block(design: dict) -> str:
    """Render the Architect's contract as explicit build instructions."""
    if not design or not design.get("endpoints"):
        return ""
    lines = [
        "DESIGN CONTRACT (implement EXACTLY — endpoint paths, methods, and table",
        "schema must match; your tests must verify these endpoints):",
        f"Module: features/{design.get('module', 'feature')}.py  "
        f"(tests: tests/test_{design.get('module', 'feature')}.py)",
    ]
    if design.get("tables"):
        lines.append("Tables:")
        for t in design["tables"]:
            cols = ", ".join(t.get("columns", []))
            lines.append(f"- {t.get('name', '?')}({cols})")
    lines.append("Endpoints:")
    for e in design["endpoints"]:
        req = e.get("request")
        res = e.get("response")
        extra = []
        if req:
            extra.append(f"request={req}")
        if res:
            extra.append(f"response={res}")
        meta = ("  " + "  ".join(extra)) if extra else ""
        lines.append(f"- {e.get('method', 'GET')} {e.get('path', '/api/')}{meta}"
                     f"  — {e.get('description', '')}")
    if design.get("notes"):
        lines.append(f"Notes: {design['notes']}")
    return "\n".join(lines)


def _build_user_prompt(state: GhostCorpState, failing_output: str | None) -> str:
    feature = state["current_feature"]
    criteria = feature.get("acceptance_criteria", [])
    crit_text = "\n".join(f"- {c}" for c in criteria) if criteria else "- Implement the feature sensibly."

    existing = [
        f for f in ws.list_files()
        if f.startswith("features/") and f.endswith(".py") and f != "features/__init__.py"
    ]

    parts = [
        f"PRODUCT: {state['product_name']} — {state['product_vision']}",
        "",
        "FEATURE TO BUILD:",
        f"Title: {feature.get('title', 'Untitled')}",
        f"Description: {feature.get('description', '')}",
        "Acceptance criteria:",
        crit_text,
    ]

    design_block = _design_block(feature.get("design", {}))
    if design_block:
        parts += ["", design_block]

    parts += ["", f"EXISTING FEATURE MODULES: {', '.join(existing) if existing else 'none'}"]

    if failing_output:
        # Retry: show the failure and the current code so the Engineer can fix it.
        current = []
        for f in (state.get("current_feature", {}).get("_files") or []):
            content = ws.read_file(f)
            if content is not None:
                current.append(f"--- {f} ---\n{content}")
        parts += [
            "",
            "YOUR PREVIOUS ATTEMPT FAILED THE TEST SUITE. Fix the code so all tests pass.",
            "TEST OUTPUT:",
            failing_output[-2500:],
            "",
            "CURRENT FILES:",
            "\n\n".join(current) if current else "(none written)",
        ]

    parts += ["", "Output the file blocks now."]
    return "\n".join(parts)


async def engineer_agent(state: GhostCorpState, failing_output: str | None = None) -> dict:
    """Generate + write feature files. Returns {files, summary}."""
    user = _build_user_prompt(state, failing_output)

    try:
        raw = await ainvoke(engineer_llm, SYSTEM_PROMPT, user)
    except Exception as exc:
        log_agent(state, "Engineer", f"code generation failed: {exc}")
        return {"files": [], "summary": f"generation error: {exc}"}

    blocks = parse_file_blocks(raw)
    written = []
    skipped = []
    for block in blocks:
        if _allowed(block["path"]):
            ws.write_file(block["path"], block["content"])
            written.append(block["path"])
        else:
            skipped.append(block["path"])

    # Remember which files this feature owns (used to show current code on retry).
    state.setdefault("current_feature", {})["_files"] = written

    summary = f"wrote {len(written)} file(s)"
    if skipped:
        summary += f" (skipped disallowed: {', '.join(skipped)})"
    log_agent(state, "Engineer", f"{summary}: {', '.join(written) if written else '(no valid file blocks)'}")
    return {"files": written, "summary": summary}
