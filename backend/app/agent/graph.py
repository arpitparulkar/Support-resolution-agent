"""Compatibility import for the V2 supervisor/specialist graph."""

from backend.app.agent.multi_agent import build_graph, classify_intent

__all__ = ["build_graph", "classify_intent"]
