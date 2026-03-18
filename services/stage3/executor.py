"""
Stage 3 Executor — interface and default implementation.

Provides a base class for Stage 3 execution strategies, allowing
future alternate executors (cached, replay, local) while keeping
the current Foundry Agent + Code Interpreter flow as the default.
"""

from abc import ABC, abstractmethod

from services.agent_extraction_service import run_agent_extraction
from services.validation_service import post_process_and_validate


class Stage3Executor(ABC):
    """Abstract base class for Stage 3 extraction execution."""

    @abstractmethod
    def execute(
        self,
        image_path: str,
        geometry: dict,
        discovery: dict,
        wire_map: str,
        console=None,
        foundry_service=None,
        output_path: str | None = None,
    ) -> tuple[dict, float]:
        """Execute Stage 3 extraction.

        Args:
            image_path: Path to the schematic image.
            geometry: Stage 1 geometry dict.
            discovery: Stage 2 discovery dict.
            wire_map: Formatted wire map text.
            console: Rich Console for output.
            foundry_service: FoundryService instance.
            output_path: Optional path to save final output.

        Returns:
            Tuple of (extraction_dict, elapsed_seconds).
        """
        ...


class DefaultAgenticExecutor(Stage3Executor):
    """Default executor — Foundry Agent + Code Interpreter.

    This is the current production path that achieves 95-99% accuracy.
    It delegates to the existing agent_extraction_service and validation_service.
    """

    def execute(
        self,
        image_path: str,
        geometry: dict,
        discovery: dict,
        wire_map: str,
        console=None,
        foundry_service=None,
        output_path: str | None = None,
    ) -> tuple[dict, float]:
        """Execute Stage 3 via Foundry Agent + Code Interpreter."""
        parsed, elapsed = run_agent_extraction(
            image_path, geometry, discovery, wire_map, console, foundry_service
        )

        parsed = post_process_and_validate(
            parsed, geometry, discovery, console,
            elapsed=elapsed, output_path=output_path,
        )

        return parsed, elapsed
