"""
core/graph.py — LangGraph StateGraph definition for SimCorp.

Stage 2 wires the money loop as a linear supervisor pipeline:

    START -> ceo -> finance -> sales -> END

The Competitor node (which runs *before* the CEO) and the parallel simplified
agents are added in later stages. The tick engine (core/tick.py) orchestrates
the same agent coroutines directly for fine-grained async control; this compiled
graph is the canonical LangGraph artifact for LangSmith tracing and inspection.
"""

from __future__ import annotations

from core.state import SimCorpState
from agents.ceo_agent import ceo_agent
from agents.finance_agent import finance_agent
from agents.sales_agent import sales_agent


def _memory_checkpointer():
    """Return an in-memory LangGraph checkpointer (name varies by version)."""
    try:
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver()
    except ImportError:  # older langgraph
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()


def build_graph(checkpointer=None):
    """Compile and return the SimCorp StateGraph.

    Built lazily (function, not module-level) so importing this module never
    requires an API key or a running NIM endpoint.
    """
    from langgraph.graph import StateGraph, START, END

    graph = StateGraph(SimCorpState)
    graph.add_node("ceo", ceo_agent)
    graph.add_node("finance", finance_agent)
    graph.add_node("sales", sales_agent)

    graph.add_edge(START, "ceo")
    graph.add_edge("ceo", "finance")
    graph.add_edge("finance", "sales")
    graph.add_edge("sales", END)

    return graph.compile(checkpointer=checkpointer or _memory_checkpointer())
