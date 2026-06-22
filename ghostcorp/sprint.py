"""
ghostcorp/sprint.py — the sprint engine.

Owns both the inner build loop (Engineer <-> QA) and the full autonomous sprint
that ties the whole company together:

    CEO founds/prioritizes  ->  PM specs  ->  Engineer <-> QA build  ->  DevOps ships

The Engineer writes real code, QA runs the real test suite, and on failure the
real failing output is fed back for a bounded number of retries. If a feature
still won't go green, the loop reverts the workspace so the product stays
shippable. DevOps only ships green builds — versioned, changelogged, committed.
"""

from __future__ import annotations

from ghostcorp import workspace as ws
from ghostcorp.agents._common import log_agent
from ghostcorp.agents.architect_agent import architect_agent
from ghostcorp.agents.devops_agent import devops_agent
from ghostcorp.agents.engineer_agent import engineer_agent
from ghostcorp.agents.founder_agent import founder_agent
from ghostcorp.agents.pm_agent import pm_agent
from ghostcorp.agents.qa_agent import qa_agent
from ghostcorp.state import GhostCorpState, new_state, sprint_snapshot

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


def init_company(force: bool = True) -> GhostCorpState:
    """Seed a fresh product workspace and return a Sprint 0 state.

    The CEO hasn't chosen a product yet — that happens on the first run_sprint().
    """
    ws.init_workspace(force=force)
    state = new_state()
    state["files"] = ws.list_files()
    state["commits"] = ws.git_log()
    return state


def _mark_blocked(state: GhostCorpState) -> None:
    feature = state.get("current_feature", {})
    for item in state["backlog"]:
        if item.get("id") == feature.get("id"):
            item["status"] = "blocked"
            break


async def run_sprint(state: GhostCorpState) -> GhostCorpState:
    """Run one full autonomous sprint and return the updated state.

    CEO founds (first sprint) / prioritizes -> PM specs -> Engineer<->QA build ->
    DevOps ships on green (or the feature is marked blocked). A per-sprint
    snapshot is appended for the dashboard timeline.
    """
    state["sprint"] += 1
    state["build_attempts"] = 0
    state["last_diff"] = ""

    # 1) CEO: invent the product (first sprint) and pick the next feature.
    await founder_agent(state)

    # 2) PM: turn the idea into a testable spec.
    await pm_agent(state)

    # 3) Architect: define the data model + REST contract before any code.
    await architect_agent(state)

    # 4) Engineer <-> QA: build it for real until green (or give up).
    shipped = await build_feature(state)

    # 5) DevOps: ship the green build, or mark the feature blocked.
    if shipped:
        await devops_agent(state)
    else:
        _mark_blocked(state)
        state["status"] = "idle"

    state["sprint_history"].append(sprint_snapshot(state))
    return state


async def run_sprints(state: GhostCorpState, n: int) -> GhostCorpState:
    """Run n consecutive sprints (used by the CLI / API run loop)."""
    for _ in range(n):
        await run_sprint(state)
    return state
