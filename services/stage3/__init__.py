"""
Schematic-IQ Stage 3 — Agentic Extraction Module.

Provides a Stage3Executor interface for running extraction,
with the default implementation using the current Foundry Agent + Code Interpreter flow.
"""

from services.stage3.executor import Stage3Executor, DefaultAgenticExecutor

__all__ = ["Stage3Executor", "DefaultAgenticExecutor"]
