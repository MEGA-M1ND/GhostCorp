# 👻 GhostCorp — An Autonomous AI Software Company

> A company with **no humans** that builds **real software**. A team of AI agents —
> powered by **NVIDIA Nemotron** via NVIDIA NIM and orchestrated with **LangGraph** —
> invents a SaaS product, then designs, writes, **tests, and ships** it one sprint
> at a time. The code is real. The tests actually run. The product is live.

Built for the **NVIDIA × OpenACC × Gnani.ai India Agentic AI Open Hackathon 2026
(Track A: Agentic Workflows)**.

---

## What makes it different

Most "AI company" demos are simulations — numbers moving on a chart. **GhostCorp
produces a working product you can open in a browser.** Every sprint:

- the **CEO** (Nemotron-70B) decides *what to build* — it invents the product,
  writes the vision, and prioritizes the backlog;
- the **PM** turns the next idea into a testable spec;
- the **Architect** (Nemotron-70B) designs the SQLite schema + REST contract
  *before any code is written* (a MetaGPT-style SOP that makes codegen reliable);
- the **Engineer** (Nemotron-70B) writes real FastAPI + SQLite code against that
  contract, into a git-backed workspace;
- **QA** runs the **actual pytest suite** — green/red is real, not a score;
- **DevOps** ships only green builds: bumps the version, writes the changelog,
  and commits to the product's own git history.

If the Engineer's code fails the tests, QA sends the **real failing output** back
and it tries again. If it still can't pass, the workspace reverts to the last
green build — so the product is **never left broken**.

> The hero moment: hit **Run Sprint** on a fresh company and watch the CEO invent
> a product out of nothing, then watch real code appear, real tests go green, and
> the **live preview** of the running app update — all with no human in the loop.

---

## Architecture

```
   ┌──────────────────────────────────────────────────────────────┐
   │  CEO / Founder  (Nemotron-70B)                                │
   │  invents the product · vision · prioritizes the backlog       │
   └───────────────────────────┬──────────────────────────────────┘
                               │ next feature
                               ▼
   ┌──────────┐ spec ┌────────────┐ schema+ ┌──────────────┐ code ┌────────────┐
   │  PM (8B) │ ───▶ │ Architect  │ contract│ Engineer(70B)│ ───▶ │ workspace/ │
   │ criteria │      │ (70B) data │ ──────▶ │ writes code +│      │ product/   │
   │          │      │ model+API  │         │ pytest tests │      │ (git repo) │
   └──────────┘      └────────────┘         └──────┬───────┘      └─────┬──────┘
                                                   │                     │
                                   fails ◀── real pytest ──┐            │
                                   (retry) │   QA (8B)     │ green       ▼
                                           └──────┬────────┘    ┌────────────────────┐
                                                  │ approved    │  Live product      │
                                                  ▼             │  (uvicorn :8100)   │
                                          ┌──────────────┐ commit│  served in an      │
                                          │ DevOps (8B)  │ ────▶ │  iframe preview    │
                                          │ version·ship │       └────────────────────┘
                                          └──────────────┘

   SHARED STATE : GhostCorpState (sprint, backlog, version, changelog, files, tests)
   EXECUTION    : real subprocess pytest runner (the credibility anchor)
   WORKSPACE    : a real, git-backed product that grows commit by commit
   UI           : FastAPI control plane + single-file dashboard (1.5s polling)
```

**Sprint order** (one tick = one sprint):
`CEO founds/prioritizes → PM specs → Architect designs → Engineer ⇄ QA (build + real tests) → DevOps ships`

---

## Tech stack

| Layer | Technology |
|---|---|
| CEO + Architect + Engineer LLM | `nvidia/llama-3.1-nemotron-70b-instruct` (NVIDIA NIM) |
| PM / QA / DevOps LLM | `nvidia/llama-3.1-nemotron-nano-8b-v1` (NVIDIA NIM) |
| LLM client | `langchain-nvidia-ai-endpoints` (`ChatNVIDIA`) |
| Test execution | real `pytest` in a sandboxed subprocess |
| Product workspace | git-backed FastAPI + SQLite app |
| API / dashboard | FastAPI + single-file HTML/JS mission control |
| Observability | LangSmith (optional, one env var) |
| Runtime | Python 3.11+, `asyncio` |

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your key
cp .env.example .env
#   edit .env: add NVIDIA_API_KEY (from build.nvidia.com)

# 3. Check everything is wired up
python -m ghostcorp doctor

# 4a. Launch mission control (dashboard + live product preview)
python -m ghostcorp serve
#   → http://localhost:8000   (the product preview runs on :8100)

# 4b. …or run it headless in the terminal
python -m ghostcorp run --sprints 5
```

No API key yet? `python -m ghostcorp doctor` and the offline test suites still
run — the company just can't generate code until you add a key.

---

## Using mission control

1. Open **http://localhost:8000**.
2. Press **▶ Run Sprint** (or **▶▶ Run 3**). Watch the activity feed: the CEO
   founds the company, the PM specs a feature, the Engineer writes code, QA runs
   the real suite, DevOps ships.
3. The **Live Product Preview** iframe reloads as the product gains features.
   The **Codebase** panel shows the growing file tree and the latest diff; the
   **Changelog** shows every shipped version.
4. **↻ Reset** seeds a brand-new company (the CEO will invent a *different*
   product).

---

## Control-plane API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/state` | Full company state (+ running flag, preview URL) |
| `POST` | `/api/sprint/run?n=1` | Run N autonomous sprints (background, serialized) |
| `POST` | `/api/reset` | Seed a fresh company / workspace |
| `POST` | `/api/preview/restart` | Restart the live product preview |
| `GET` | `/` | Mission-control dashboard |

---

## How the product gets built (reliability)

- **Fixed shape, free idea.** The CEO chooses *what* to build; the *technical
  shape* is fixed (FastAPI + SQLite + auto-mounted feature modules) so codegen
  and tests stay tractable no matter what product it dreams up.
- **Design before code.** The Architect emits an explicit schema + endpoint
  contract that the Engineer implements and QA tests against — a MetaGPT-style
  SOP that sharply raises the first-attempt pass rate over free-form codegen.
- **Auto-wiring.** The app discovers any `features/<name>.py` exposing a
  `router`, so the Engineer writes one self-contained module instead of editing
  shared files — far more reliable than multi-file surgery.
- **Reality is the gate.** `passed` comes from the real pytest exit code, never
  the LLM. QA's note is just narration.
- **Bounded retries + safe revert.** Up to 3 Engineer⇄QA rounds with the real
  failing output fed back; if it still won't go green, the workspace reverts to
  the last green commit. The product is always shippable.
- **Graceful degradation.** Every LLM call has retry + JSON fallback, and the CEO
  has a fallback product, so a bad response never dead-ends a demo.

---

## Project structure

```
ghostcorp/
  seed/          the runnable product skeleton (FastAPI+SQLite+HTML+tests) — Sprint 0
  workspace.py   git-backed product workspace (read/write/commit/diff)
  executor.py    REAL pytest runner (subprocess + timeout + parsed verdict)
  state.py       GhostCorpState (sprint, backlog, version, changelog, tests…)
  llms.py        role-based NIM clients (Founder/Engineer 70B · PM/QA/DevOps 8B)
  agents/        founder · pm · architect · engineer · qa · devops
  sprint.py      build loop (Engineer⇄QA) + full run_sprint orchestration
  product_server.py   runs the AI's product as a live subprocess (preview)
  server.py      FastAPI control plane (state/run/reset)
  dashboard.html single-file mission control
  cli.py         `python -m ghostcorp {serve,run,doctor}`
workspace/product/   ← the AI's product is materialized here at runtime (own git repo)
```

---

## CLI

```bash
python -m ghostcorp serve [--port 8000] [--reload]   # dashboard + live preview
python -m ghostcorp run --sprints 5                  # headless terminal demo
python -m ghostcorp doctor                           # config + dependency check
```

---

## Observability

Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` in `.env` and every agent
call — including the CEO's product-invention reasoning and the Engineer's
codegen — appears as a trace at [smith.langchain.com](https://smith.langchain.com)
under the `ghostcorp-hackathon` project. No code changes required.

---

## Legacy: SimCorp business-simulation mode

GhostCorp evolved from **SimCorp**, a multi-agent *simulation* of an AI-run SaaS
business (CEO, finance, sales, marketing, product, customer, and an adversarial
competitor advancing KPIs — ARR, burn, churn, market share — quarter by quarter).
That system still ships in this repo under `core/`, `agents/`, `simulation/`,
`api/`, and `dashboard/`, and runs via:

```bash
python run.py            # http://localhost:8000  (simulation dashboard)
python tests/test_agents.py
```

GhostCorp (the autonomous *software company* above) is the primary system; the
simulation remains as an optional, self-contained mode.
