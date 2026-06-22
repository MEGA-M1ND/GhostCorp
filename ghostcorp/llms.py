"""
ghostcorp/llms.py — LLM clients for the AI company's roles.

Reuses the NVIDIA NIM client factory from core.config. The CEO/Founder and the
Engineer run on Nemotron-70B (strategy + code quality matter most); the lighter
roles run on Nemotron-nano-8B. Clients are lazy — importing this module never
requires an API key.
"""

from __future__ import annotations

from core.config import _LazyLLM, get_ceo_llm, get_fast_llm

# Founder/CEO — picks the product, sets vision, prioritizes the backlog (70B).
founder_llm = _LazyLLM(lambda: get_ceo_llm(temperature=0.6, max_tokens=1100))

# Engineer — writes real code; needs headroom and low temperature (70B).
engineer_llm = _LazyLLM(lambda: get_ceo_llm(temperature=0.2, max_tokens=3000))

# Product Manager — turns direction into a crisp spec (8B).
pm_llm = _LazyLLM(lambda: get_fast_llm(temperature=0.4, max_tokens=700))

# QA — reviews the real test verdict and writes a short note (8B).
qa_llm = _LazyLLM(lambda: get_fast_llm(temperature=0.3, max_tokens=400))

# DevOps — ship notes / changelog summaries (8B).
devops_llm = _LazyLLM(lambda: get_fast_llm(temperature=0.3, max_tokens=400))
