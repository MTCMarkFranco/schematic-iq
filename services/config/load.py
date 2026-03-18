"""
Configuration loading — environment variables, optional YAML, and CLI overrides.

Priority (highest to lowest):
  1. CLI arguments / explicit overrides
  2. Environment variables
  3. config.yaml (if present)
  4. Built-in defaults
"""

import os
from pathlib import Path

from services.config.defaults import get_defaults
from services.config.types import PipelineConfig


def load_config(config_path: str | None = None) -> PipelineConfig:
    """Load pipeline configuration from defaults + env vars + optional YAML.

    This function merges configuration sources in priority order.
    Currently: defaults → environment variables.
    YAML support is scaffolded for future use.

    Args:
        config_path: Optional path to a config.yaml file.

    Returns:
        Fully resolved PipelineConfig.
    """
    config = get_defaults()

    # Layer 2: Optional YAML file
    if config_path and Path(config_path).exists():
        _apply_yaml(config, config_path)

    # Layer 3: Environment variables (highest priority)
    _apply_env(config)

    # Propagate derived values
    if not config.stage2.model:
        config.stage2.model = config.azure.openai_mini_deployment

    return config


def _apply_env(config: PipelineConfig) -> None:
    """Apply environment variable overrides to config."""
    # Azure
    if v := os.getenv("AZURE_OPENAI_ENDPOINT"):
        config.azure.openai_endpoint = v
    if v := os.getenv("AZURE_OPENAI_API_VERSION"):
        config.azure.openai_api_version = v
    if v := os.getenv("AZURE_OPENAI_MINI_DEPLOYMENT"):
        config.azure.openai_mini_deployment = v
    if v := os.getenv("AZURE_AI_PROJECT_ENDPOINT"):
        config.azure.ai_project_endpoint = v

    # Stage 2
    if v := os.getenv("DISCOVERY_RUNS"):
        config.stage2.num_runs = int(v)
    if v := os.getenv("DISCOVERY_MAX_TOKENS"):
        config.stage2.max_tokens = int(v)

    # Stage 3
    if v := os.getenv("AGENT_NAME"):
        config.stage3.agent_name = v
    if v := os.getenv("AGENT_MODEL"):
        config.stage3.agent_model = v

    # Pipeline
    if v := os.getenv("PIPELINE_MODE"):
        config.pipeline_mode = v
    if v := os.getenv("OUTPUT_DIR"):
        config.output_dir = v


def _apply_yaml(config: PipelineConfig, yaml_path: str) -> None:
    """Apply YAML configuration overrides (scaffolded for future use).

    Currently a no-op if PyYAML is not installed.
    """
    try:
        import yaml
    except ImportError:
        return

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        return

    # Azure section
    if azure := data.get("azure"):
        for key in ("openai_endpoint", "openai_api_version", "openai_mini_deployment", "ai_project_endpoint"):
            if key in azure:
                setattr(config.azure, key, azure[key])

    # Stage configs
    for stage_key, stage_config in [("stage1", config.stage1), ("stage2", config.stage2), ("stage3", config.stage3)]:
        if stage_data := data.get(stage_key):
            for key, value in stage_data.items():
                if hasattr(stage_config, key):
                    setattr(stage_config, key, value)

    # Top-level
    if v := data.get("pipeline_mode"):
        config.pipeline_mode = v
    if v := data.get("output_dir"):
        config.output_dir = v
