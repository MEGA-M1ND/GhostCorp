"""
core/config.py — NVIDIA NIM endpoints + model configuration for GhostCorp.

This module is the single source of truth for LLM clients. Every agent imports
its client from here so that model selection, API keys, and tracing are
configured in exactly one place.

  - CEO Agent  -> `ceo_llm`  (Nemotron-70B, the strategic supervisor)
  - All others -> `fast_llm` (Nemotron-nano-8B, fast + cheap, runs in parallel)

Keys are loaded from `.env` via python-dotenv. Nothing is ever hardcoded.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

# Load .env once at import time. Real keys live in .env (gitignored); the
# template lives in .env.example.
load_dotenv()


# ---------------------------------------------------------------------------
# Model + endpoint configuration
# ---------------------------------------------------------------------------

# CEO must run on Nemotron-70B — judges will check. Everyone else uses nano-8B.
CEO_MODEL: str = os.getenv("CEO_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct")
FAST_MODEL: str = os.getenv("FAST_MODEL", "nvidia/llama-3.1-nemotron-nano-8b-v1")

# OpenAI-compatible NVIDIA NIM endpoint. ChatNVIDIA defaults to this, but we
# allow an override so the sim can point at a self-hosted NIM container.
NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

NVIDIA_API_KEY: str | None = os.getenv("NVIDIA_API_KEY")

# LangSmith tracing is enabled purely via env vars (LANGCHAIN_TRACING_V2,
# LANGCHAIN_API_KEY, LANGCHAIN_PROJECT). No code change needed — we just surface
# the project name for logging/diagnostics.
LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "ghostcorp-hackathon")
LANGSMITH_TRACING: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"


class MissingNvidiaKeyError(RuntimeError):
    """Raised when an LLM client is requested but NVIDIA_API_KEY is not set."""


def _require_key() -> str:
    if not NVIDIA_API_KEY:
        raise MissingNvidiaKeyError(
            "NVIDIA_API_KEY is not set. Copy .env.example to .env and add your "
            "key from https://build.nvidia.com (format: nvapi-...)."
        )
    return NVIDIA_API_KEY


@lru_cache(maxsize=None)
def _build_llm(model: str, temperature: float, max_tokens: int):
    """Construct (and cache) a ChatNVIDIA client.

    Imported lazily so that merely importing this module does not require the
    langchain-nvidia-ai-endpoints package to be installed (useful for unit
    tests that only touch state/config constants).
    """
    api_key = _require_key()  # fail fast on the most common misconfiguration
    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    return ChatNVIDIA(
        model=model,
        api_key=api_key,
        base_url=NVIDIA_BASE_URL,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_ceo_llm(temperature: float = 0.4, max_tokens: int = 1024):
    """The CEO supervisor — Nemotron-70B. Slightly creative, decisive."""
    return _build_llm(CEO_MODEL, temperature, max_tokens)


def get_fast_llm(temperature: float = 0.3, max_tokens: int = 512):
    """Worker agents — Nemotron-nano-8B. Lower temperature for terse JSON."""
    return _build_llm(FAST_MODEL, temperature, max_tokens)


# Convenience module-level singletons. These are lazy in the sense that the
# underlying ChatNVIDIA client is only built on first attribute access via the
# functions above; importing the names below *does* build them, so prefer the
# getters in code paths that must run without an API key (e.g. tests).
class _LazyLLM:
    """A thin proxy that builds the real client on first use."""

    def __init__(self, factory):
        self._factory = factory
        self._client = None

    def _ensure(self):
        if self._client is None:
            self._client = self._factory()
        return self._client

    def __getattr__(self, name):
        return getattr(self._ensure(), name)


ceo_llm = _LazyLLM(get_ceo_llm)
fast_llm = _LazyLLM(get_fast_llm)


def connectivity_summary() -> dict:
    """Lightweight, key-free snapshot of how the LLM layer is configured."""
    return {
        "ceo_model": CEO_MODEL,
        "fast_model": FAST_MODEL,
        "base_url": NVIDIA_BASE_URL,
        "nvidia_key_present": bool(NVIDIA_API_KEY),
        "langsmith_tracing": LANGSMITH_TRACING,
        "langsmith_project": LANGCHAIN_PROJECT,
    }
