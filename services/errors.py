"""
Error taxonomy for the schematic-iq pipeline.

Defines a hierarchy of typed exceptions so callers can distinguish
which stage failed and react appropriately.  The base class
``PipelineError`` carries an ``exit_code`` that ``main.py`` translates
into a process exit code for CI/CD integration.
"""


class PipelineError(Exception):
    """Base class for all pipeline errors."""

    exit_code: int = 1

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


class Stage1Error(PipelineError):
    """Raised when OpenCV geometry extraction fails."""

    exit_code = 10


class Stage2Error(PipelineError):
    """Raised when LLM discovery fails or returns unusable output."""

    exit_code = 20


class Stage3Error(PipelineError):
    """Raised when agent extraction fails or returns unusable output."""

    exit_code = 30


class SchemaError(PipelineError):
    """Raised when final output fails JSON Schema validation."""

    exit_code = 40

    def __init__(self, message: str, *, validation_errors: list[str] | None = None):
        super().__init__(message, details={"validation_errors": validation_errors or []})
        self.validation_errors = validation_errors or []


class ConfigError(PipelineError):
    """Raised when configuration is invalid or missing."""

    exit_code = 50
