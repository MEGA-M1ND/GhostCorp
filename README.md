# SimCorp — An Entire Company in a Graph

> A multi-agent simulation of a **fully AI-operated SaaS startup**. Seven
> autonomous agents — powered by **NVIDIA Nemotron** via NVIDIA NIM and
> orchestrated with **LangGraph** — run every function of the business each
> quarter. No humans in the loop.

Built for the **NVIDIA × OpenACC × Gnani.ai India Agentic AI Open Hackathon 2026
(Track A: Agentic Workflows)**.

---

## What it is

SimCorp is a live, observable business simulation. Press **Next Quarter** and
watch a CEO agent set strategy in reaction to an adversarial competitor, while
finance, sales, product, marketing, and customer agents turn that strategy into
ARR, burn, churn, and market share — all rendered on a real-time dashboard and
fully traced in LangSmith.

The hero moment: load the **Crisis** scenario, where a rival just raised $15M and
runway is thin, and watch the CEO agent *autonomously pivot to cost-cutting*.

---

## Architecture

```
                         ┌───────────────────────────────┐
   Competitor Agent ───▶ │  CEO AGENT  (Nemotron-70B)     │  supervisor
   (nano-8B, adversary)  │  sets quarterly strategy       │
                         └───────────────┬───────────────┘
                                         │ directive + budget
            ┌────────────────────────────┼────────────────────────────┐
            ▼ (parallel, nano-8B)        ▼                             ▼
       Product Agent              Marketing Agent               Customer Agent
       features/quality           CAC adjustment                NPS / churn
            └────────────────────────────┼────────────────────────────┘
                                         ▼
                    Finance Agent (nano-8B) ──▶ Sales Agent (nano-8B)
                    ARR / burn / runway         customers / CAC / share

   SHARED STATE : LangGraph SimCorpState (single source of truth)
   PERSISTENCE  : SQLite (per-quarter snapshots) + in-memory checkpointer
   OBSERVABILITY: LangSmith tracing (one env var, zero code change)
   UI           : FastAPI REST + single-file React/Chart.js dashboard (2s polling)
```

**Tick order** (one tick = one business quarter):
`Competitor → CEO → [Product ‖ Marketing ‖ Customer] → Finance → Sales → persist`

Six LLM calls per quarter — comfortably within the NVIDIA NIM free-tier 40 RPM.

---

## Tech stack

| Layer | Technology |
|---|---|
| CEO LLM | `nvidia/llama-3.1-nemotron-70b-instruct` (NVIDIA NIM) |
| Worker LLM | `nvidia/llama-3.1-nemotron-nano-8b-v1` (NVIDIA NIM) |
| LLM client | `langchain-nvidia-ai-endpoints` (`ChatNVIDIA`) |
| Orchestration | LangGraph (`StateGraph`, supervisor pattern) |
| Persistence | SQLite + LangGraph in-memory checkpointer |
| API | FastAPI |
| Dashboard | React 18 + Chart.js via CDN (no build step) |
| Observability | LangSmith |
| Runtime | Python 3.11+, `asyncio` |

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your keys
cp .env.example .env
#   edit .env: add NVIDIA_API_KEY (build.nvidia.com)
#   and optionally LANGCHAIN_API_KEY (smith.langchain.com)

# 3. Launch everything (server + dashboard)
python run.py
#   opens http://localhost:8000

# 4. (optional) run the offline test suite — no API key needed
python tests/test_agents.py
```

Prefer the classic dev command? `uvicorn api.main:app --reload`.

---

## Using the dashboard

1. Pick a scenario from the dropdown: **MVP Launch**, **Scale Up**, or **Crisis**.
2. Press **▶ Next Quarter** to run one tick. KPI cards, charts, the agent
   activity feed, and the CEO strategy panel update within ~2 seconds.
3. **⟳ Reset** returns to the scenario's initial conditions.

For the demo, run **Crisis** and step through 2–3 quarters to watch the CEO pivot.

---

## REST API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/state` | Full `SimCorpState` |
| `POST` | `/api/start` | Mark the simulation running |
| `POST` | `/api/next-tick` | Run one quarter (async, serialized) |
| `POST` | `/api/reset` | Reset to current scenario |
| `POST` | `/api/scenario/{name}` | Load `mvp_launch` \| `scale_up` \| `crisis` |
| `GET` | `/api/metrics` | History array (chart data) |
| `GET` | `/api/agent-log` | Agent activity log |
| `GET` | `/` | Dashboard |

---

## Project structure

```
core/        state.py · config.py · graph.py · tick.py · persistence.py
agents/      ceo · finance · sales · competitor · product · marketing · customer · _common
tools/       financial_tools.py
simulation/  market_engine.py · scenarios/{mvp_launch,scale_up,crisis}.py
api/         main.py · sim_service.py · routes/{simulation,metrics}.py
dashboard/   index.html  (single-file React + Chart.js)
tests/       test_agents.py  (offline, stubbed LLMs)
run.py       one-command startup
```

---

## Scenarios

| Scenario | Setup | Story |
|---|---|---|
| **MVP Launch** | Q1, $120K ARR, 17.8mo runway | Seed-stage growth from scratch |
| **Scale Up** | Q4, $1.8M ARR, 18mo runway, winning | Compounding growth, competitor on the back foot |
| **Crisis** *(demo hero)* | Q3, $1.5M ARR, ~9mo runway, rival raised $15M | Pivot or die — the CEO must cut burn |

---

## How the agents stay reliable

Each agent's **qualitative judgment is LLM-driven** (the CEO's strategy and
reasoning, the competitor's chosen move), while the **KPI arithmetic is
deterministic** (`tools/financial_tools.py`, `simulation/market_engine.py`). This
keeps demo numbers legible and stable while the decisions remain genuinely
autonomous. Hard guard-rails enforce the CEO's non-negotiable behaviors (e.g.
runway < 6 months ⇒ cost-cut), and every LLM call has exponential-backoff retry
plus a JSON fallback, so a malformed response never breaks a tick.

---

## Observability

Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` in `.env` and every agent
call — including the CEO's full reasoning chain — appears as a trace at
[smith.langchain.com](https://smith.langchain.com) under the
`simcorp-hackathon` project. No code changes required.
