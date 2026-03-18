"""
Default configuration values for Schematic-IQ pipeline.

All defaults match the current production behavior exactly.
"""

from services.config.types import (
    AzureConfig,
    PipelineConfig,
    Stage1Config,
    Stage2Config,
    Stage3Config,
)


def get_defaults() -> PipelineConfig:
    """Return the default pipeline configuration.

    These defaults match the current hardcoded values across all services,
    ensuring zero behavior change when adopting the config layer.
    """
    return PipelineConfig(
        azure=AzureConfig(
            openai_endpoint="",
            openai_api_version="2024-12-01-preview",
            openai_mini_deployment="gpt-4o-mini",
            ai_project_endpoint="",
        ),
        stage1=Stage1Config(
            kernel_length=60,
            dilate_size=3,
            hough_threshold=30,
            min_line_length=60,
            max_line_gap=20,
            merge_gap=15,
            group_tolerance=8,
            min_segment_length=30,
            join_radius=15,
        ),
        stage2=Stage2Config(
            num_runs=3,
            max_tokens=14_000,
            temperature=0.8,
        ),
        stage3=Stage3Config(
            agent_name="schematic-iq-extractor",
            agent_model="gpt-5.4-pro",
            stream_timeout=900,
            max_retries=2,
            retry_base_delay=30,
            thumbnail_max_dim=1024,
        ),
        pipeline_mode="v1",
        output_dir="output",
    )
