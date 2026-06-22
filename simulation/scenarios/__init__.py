"""Pre-built GhostCorp scenarios (initial states for the simulation)."""

from importlib import import_module

# Map of scenario name -> module path. The crisis/scale_up modules are added in
# later build stages; mvp_launch is the Stage 2 default.
SCENARIO_MODULES = {
    "mvp_launch": "simulation.scenarios.mvp_launch",
    "scale_up": "simulation.scenarios.scale_up",
    "crisis": "simulation.scenarios.crisis",
}


def load_scenario(name: str) -> dict:
    """Return a fresh INITIAL_STATE dict for the named scenario.

    Falls back to mvp_launch for unknown names. Returns a deep-ish copy so the
    caller can mutate freely without corrupting the module-level template.
    """
    import copy

    module_path = SCENARIO_MODULES.get(name, SCENARIO_MODULES["mvp_launch"])
    module = import_module(module_path)
    return copy.deepcopy(module.INITIAL_STATE)
