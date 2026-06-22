"""
ghostcorp/cli.py — command-line entry point for GhostCorp.

  python -m ghostcorp serve              launch the mission-control dashboard
  python -m ghostcorp run --sprints 5    run N autonomous sprints headless
  python -m ghostcorp doctor             check config + dependencies

`run` is the headless demo: the CEO invents a product and the company builds,
tests, and ships real features sprint by sprint, printed to the terminal.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from ghostcorp.sprint import init_company, run_sprint

GREEN, DIM, RED, BOLD, RESET = "\033[32m", "\033[90m", "\033[31m", "\033[1m", "\033[0m"


def _check_key() -> bool:
    from core.config import NVIDIA_API_KEY

    return bool(NVIDIA_API_KEY)


async def _run_headless(sprints: int) -> dict:
    state = init_company(force=True)
    print(f"{BOLD}👻 GhostCorp — founding a company and running {sprints} sprint(s){RESET}\n")

    seen = 0
    for i in range(sprints):
        await run_sprint(state)

        # Stream the new activity-feed entries from this sprint.
        for entry in state["agent_log"][seen:]:
            print(f"  {DIM}[{entry['agent']:<8}]{RESET} {entry['action']}")
        seen = len(state["agent_log"])

        tr = state.get("test_results", {})
        shipped = tr.get("passed")
        tag = f"{GREEN}SHIPPED v{state['version']}{RESET}" if shipped else f"{RED}BLOCKED{RESET}"
        feat = state.get("current_feature", {}).get("title", "")
        print(f"  {BOLD}Sprint {state['sprint']}:{RESET} {feat} — {tag} "
              f"({tr.get('passed_count', 0)} tests pass)\n")

    print(f"{BOLD}── Final state ─────────────────────────────{RESET}")
    print(f"  Product : {GREEN}{state['product_name']}{RESET} v{state['version']}")
    print(f"  Vision  : {state['product_vision']}")
    print(f"  Shipped : {len(state['changelog'])} feature(s)")
    for c in state["changelog"]:
        print(f"            {DIM}v{c['version']}{RESET} {c['title']}  ({c['commit']})")
    print(f"  Files   : {len(state['files'])}")
    print(f"  Workspace: {os.getenv('GHOSTCORP_WORKSPACE', 'workspace/product')}  "
          f"(run `git log` there to see the build history)")
    return state


def cmd_run(args: argparse.Namespace) -> int:
    if not _check_key():
        print(f"{RED}⚠ NVIDIA_API_KEY not set.{RESET} The CEO will use a fallback product and "
              f"the Engineer cannot generate code, so features will be BLOCKED.\n"
              f"  Copy .env.example to .env and add your key from https://build.nvidia.com\n")
    asyncio.run(_run_headless(args.sprints))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    if not _check_key():
        print(f"{RED}⚠ NVIDIA_API_KEY not set{RESET} — the dashboard will start, but sprints will "
              f"block until you add a key to .env.\n")
    print(f"{BOLD}👻 GhostCorp Mission Control{RESET} → http://localhost:{args.port}")
    uvicorn.run("ghostcorp.server:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from core.config import connectivity_summary

    print(f"{BOLD}GhostCorp preflight{RESET}\n")
    cfg = connectivity_summary()
    checks = []

    def ok(label, passed, detail=""):
        mark = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        print(f"  {mark} {label}{(' — ' + detail) if detail else ''}")
        checks.append(passed)

    ok("NVIDIA_API_KEY present", cfg["nvidia_key_present"],
       "" if cfg["nvidia_key_present"] else "set it in .env (sprints will block without it)")
    print(f"    {DIM}CEO model : {cfg['ceo_model']}{RESET}")
    print(f"    {DIM}Fast model: {cfg['fast_model']}{RESET}")

    for mod, label in [("pytest", "pytest (real test runner)"),
                       ("uvicorn", "uvicorn (server + live preview)"),
                       ("fastapi", "fastapi"),
                       ("httpx", "httpx (TestClient)")]:
        try:
            __import__(mod)
            ok(label, True)
        except Exception as exc:
            ok(label, False, str(exc))

    import shutil
    ok("git available", shutil.which("git") is not None)

    try:
        from ghostcorp import workspace as ws
        ws.init_workspace(force=True)
        from ghostcorp import executor as ex
        res = ex.run_tests(str(ws.WORKSPACE_DIR))
        ok("seed product builds & tests green", res["passed"],
           f"{res['passed_count']} passed")
    except Exception as exc:
        ok("seed product builds & tests green", False, str(exc))

    passed = all(checks)
    print(f"\n{'%s✓ All systems go%s' % (GREEN, RESET) if passed else '%s✗ Some checks failed%s' % (RED, RESET)}")
    return 0 if passed else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ghostcorp", description="GhostCorp — an autonomous AI software company.")
    sub = p.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("run", help="run N autonomous sprints headless")
    pr.add_argument("--sprints", type=int, default=3)
    pr.set_defaults(func=cmd_run)

    ps = sub.add_parser("serve", help="launch the mission-control dashboard")
    ps.add_argument("--host", default="0.0.0.0")
    ps.add_argument("--port", type=int, default=int(os.getenv("GHOSTCORP_PORT", "8000")))
    ps.add_argument("--reload", action="store_true")
    ps.set_defaults(func=cmd_serve)

    pd = sub.add_parser("doctor", help="check configuration and dependencies")
    pd.set_defaults(func=cmd_doctor)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
