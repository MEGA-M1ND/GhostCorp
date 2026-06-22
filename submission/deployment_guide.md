# SimCorp — Deployment & Demo Guide

This guide covers setup, the 2-minute demo script, troubleshooting, and the
submission checklist for the NVIDIA × OpenACC × Gnani.ai Agentic AI Hackathon 2026.

---

## 1. Prerequisites

- Python 3.11+
- An **NVIDIA NIM API key** — https://build.nvidia.com (format `nvapi-...`)
- (Recommended) a **LangSmith API key** — https://smith.langchain.com (`ls__...`)

---

## 2. Setup

```bash
git clone <repo-url> && cd GhostCorp
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
NVIDIA_API_KEY=nvapi-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=simcorp-hackathon
```

Verify connectivity:

```bash
python -c "from core.config import ceo_llm; print(ceo_llm.invoke('Say NVIDIA NIM connected').content)"
```

Run the offline test suite (no key required):

```bash
python tests/test_agents.py    # expect 6/6 passed
```

---

## 3. Launch

```bash
python run.py                  # serves API + dashboard, opens the browser
# or
uvicorn api.main:app --reload  # dev mode
```

Dashboard: **http://localhost:8000**

---

## 4. Two-minute demo script

| Time | Action | What to say |
|---|---|---|
| 0:00 | Dashboard open on **Scale Up** | "SimCorp is a SaaS company with zero human employees." |
| 0:10 | Point to KPI cards | "ARR, customers, runway — every number is produced by autonomous AI agents on NVIDIA Nemotron." |
| 0:30 | Select **Crisis**, press **Next Quarter** | "Let's drop them into a crisis." |
| 0:40 | Activity feed shows competitor move | "The rival just raised \$15M Series A." |
| 0:50 | CEO Strategy panel updates | "The CEO agent — Nemotron-70B — reads runway at ~9 months and pivots to cost-cut, autonomously." |
| 1:05 | Press **Next Quarter** again | "Burn drops, runway extends — the plan is working." |
| 1:30 | Open LangSmith trace | "Here's the full reasoning chain behind that decision." |
| 1:45 | — | "Seven agents, one LangGraph supervisor loop, zero human decisions." |
| 2:00 | — | "SimCorp. An entire company in a graph." |

**Rehearsal tip:** Reset and run Crisis 2–3 quarters beforehand so you know which
quarter the pivot lands on for *your* key/model, then start the recording one
quarter earlier.

---

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| Dashboard loads, "Next Quarter" errors | `NVIDIA_API_KEY` missing/invalid in `.env` |
| `429` from NIM | Built-in exponential-backoff retries; if persistent, slow down clicks (free tier = 40 RPM) |
| Charts empty | Run at least one quarter; charts are driven by `history` |
| No LangSmith traces | Ensure `LANGCHAIN_TRACING_V2=true` **and** `LANGCHAIN_API_KEY` are set before launch |
| State persists across restarts unexpectedly | Snapshots live in `db/simcorp.db`; **Reset** clears them |

---

## 6. Submission checklist

- [ ] `python tests/test_agents.py` → 6/6 passed
- [ ] Live NIM connectivity check returns a response
- [ ] CEO Agent confirmed on `nemotron-70b`, all others on `nemotron-nano-8b`
- [ ] Crisis scenario pivots to cost-cut on camera
- [ ] LangSmith trace screenshot captured
- [ ] 2-minute demo video recorded
- [ ] `deck.pdf` added to `submission/`

---

## 7. Notes for judges

- **Model split is enforced in `core/config.py`**: `ceo_llm` → Nemotron-70B,
  `fast_llm` → Nemotron-nano-8B.
- **Agent autonomy with guard-rails**: decisions are LLM-generated; deterministic
  guards enforce non-negotiable CEO behaviors and bound the KPI math so the
  simulation is reproducible.
- **Zero build step**: the dashboard is a single `index.html` (React + Chart.js
  via CDN) — open it through the FastAPI server, nothing to compile.
