"""
Configuration types for Schematic-IQ pipeline.

Defines structured configuration objects for all pipeline stages.
All defaults match current behavior exactly.
"""

from dataclasses import dataclass, field


@dataclass
class AzureConfig:
    """Azure service connection settings."""
    openai_endpoint: str = ""
    openai_api_version: str = "2024-12-01-preview"
    openai_mini_deployment: str = "gpt-4o-mini"
    ai_project_endpoint: str = ""


@dataclass
class Stage1Config:
    """Stage 1: OpenCV Geometry Extraction settings."""
    # Morphological kernel length (pixels, at reference scale)
    kernel_length: int = 60
    dilate_size: int = 3
    # Hough line detection
    hough_threshold: int = 30
    min_line_length: int = 60
    max_line_gap: int = 20
    # Wire merging
    merge_gap: int = 15
    group_tolerance: int = 8
    min_segment_length: int = 30
    # Chain building
    join_radius: int = 15


@dataclass
class Stage2Config:
    """Stage 2: LLM Discovery settings."""
    num_runs: int = 3
    max_tokens: int = 14_000
    temperature: float = 0.8
    model: str = ""  # Filled from AzureConfig.openai_mini_deployment


@dataclass
class Stage3Config:
    """Stage 3: Foundry Agent Extraction settings."""
    agent_name: str = "schematic-iq-extractor"
    agent_model: str = "gpt-5.4-pro"
    stream_timeout: int = 900
    max_retries: int = 2
    retry_base_delay: int = 30
    thumbnail_max_dim: int = 1024


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration."""
    azure: AzureConfig = field(default_factory=AzureConfig)
    stage1: Stage1Config = field(default_factory=Stage1Config)
    stage2: Stage2Config = field(default_factory=Stage2Config)
    stage3: Stage3Config = field(default_factory=Stage3Config)
    pipeline_mode: str = "v1"
    output_dir: str = "output"
