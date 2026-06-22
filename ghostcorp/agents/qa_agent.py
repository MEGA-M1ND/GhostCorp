"""
ghostcorp/agents/qa_agent.py — QA. Nemotron-nano-8B.

QA is the gatekeeper. The verdict (`passed`) comes from REALITY — the actual
pytest run via the executor — not from the LLM. The 8B model only writes a short
human-readable review note for the activity feed and, on failure, frames what
went wrong so the demo reads clearly.
"""

from __future__ import annotations

from ghostcorp import executor as ex
from ghostcorp import workspace as ws
from ghostcorp.agents._common import ainvoke, log_agent
from ghostcorp.llms import qa_llm
from ghostcorp.state import GhostCorpState

SYSTEM_PROMPT = (
    "You are a QA engineer at GhostCorp. Given a pytest result summary, write ONE "
    "short sentence: if it passed, approve the feature for shipping; if it failed, "
    "state plainly what is broken. No JSON, just the sentence."
)


async def qa_agent(state: GhostCorpState) -> dict:
    """Run the real test suite and attach a review note. Returns the verdict."""
    results = ex.run_tests(str(ws.WORKSPACE_DIR))
    state["test_results"] = results

    verdict = "APPROVED" if results["passed"] else "REJECTED"
    summary = (
        f"{results['passed_count']} passed, {results['failed_count']} failed, "
        f"{results['error_count']} error(s) in {results['duration']}s"
    )

    user = (
        f"Pytest result: {summary}.\n"
        f"Tail of output:\n{results['output'][-1200:]}\n"
        f"Verdict: {verdict}. Write the one-sentence review."
    )
    try:
        review = (await ainvoke(qa_llm, SYSTEM_PROMPT, user)).strip()
    except Exception:
        review = (
            "Approved for shipping." if results["passed"]
            else "Tests are failing; sending back to engineering."
        )

    log_agent(state, "QA", f"{verdict} — {summary}. {review}")
    return {"passed": results["passed"], "review": review, "results": results}
