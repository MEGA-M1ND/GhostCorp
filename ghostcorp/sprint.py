"""
ghostcorp/sprint.py — the build loop (Engineer <-> QA).

This is the heart of the "real, not simulated" claim: the Engineer writes actual
code, QA runs the actual test suite, and on failure the real failing output is
fed back to the Engineer for a bounded number of retries. If the feature still
won't go green, the loop reverts the workspace so the product stays shippable.

The full sprint (CEO picks product -> PM specs -> build_feature -> DevOps ships)
is assembled in a later stage; this module owns the build/verify inner loop.
"""

from __future__ import annotations

from ghostcorp import workspace as ws
from ghostcorp.agents._common import log_agent
from ghostcorp.agents.engineer_agent import engineer_agent
from ghostcorp.agents.qa_agent import qa_agent
from ghostcorp.state import GhostCorpState

MAX_BUILD_ATTEMPTS = 3


def _refresh_code_view(state: GhostCorpState) -> None:
    """Keep the dashboard's code view in sync with the workspace."""
    state["files"] = ws.list_files()
    state["last_diff"] = ws.working_diff()


async def build_feature(state: GhostCorpState) -> bool:
    """Run the Engineer<->QA loop for state['current_feature'].

    Returns True if the feature passed QA (changes left uncommitted in the
    workspace, ready for the DevOps agent to ship), False if the loop gave up
    (workspace reverted to the last green commit).
    """
    failing_output: str | None = None

    for attempt in range(1, MAX_BUILD_ATTEMPTS + 1):
        state["build_attempts"] = attempt
        state["status"] = "building"

        await engineer_agent(state, failing_output)
        _refresh_code_view(state)

        verdict = await qa_agent(state)
        if verdict["passed"]:
            state["status"] = "shipping"
            return True

        # Real failure -> feed the actual pytest output back for a fix.
        failing_output = verdict["results"]["output"]
        state["status"] = "blocked"

    # Out of attempts: keep the product green by discarding the broken attempt.
    ws.revert_uncommitted()
    _refresh_code_view(state)
    log_agent(
        state,
        "Engineer",
        f"feature '{state['current_feature'].get('title', '')}' abandoned after "
        f"{MAX_BUILD_ATTEMPTS} attempts; reverted to last green build.",
    )
    state["status"] = "blocked"
    return False
