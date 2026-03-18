"""
Schematic-IQ Electrical Schematic Extraction Pipeline

A 3-stage pipeline for extracting structured data from electrical schematic images:
  Stage 1: OpenCV Geometry Extraction (deterministic)
  Stage 2: LLM Discovery (component/cable/terminal inventory)
  Stage 3: Agent Extraction (Foundry Agent + Code Interpreter)

Usage:
    python main.py <image_file>

Required environment variables (.env):
    AZURE_OPENAI_ENDPOINT       - Azure OpenAI endpoint
    AZURE_OPENAI_MINI_DEPLOYMENT - gpt-4o-mini deployment name
    AZURE_AI_PROJECT_ENDPOINT   - Foundry project endpoint URL
"""

import os
import sys
import base64
import time
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich import box

from services.foundry_service import FoundryService
from services.geometry_extraction_service import (
    extract_geometry,
    format_wire_map,
)
from services.discovery_service import run_full_discovery
from services.agent_extraction_service import run_agent_extraction
from services.validation_service import post_process_and_validate
from services.telemetry import get_logger, configure_logging, PipelineMetrics
from services.errors import PipelineError, Stage1Error, Stage2Error, Stage3Error
from services.pipeline.modes import PipelineMode

# ── Initialization ───────────────────────────────────────────────────────────
load_dotenv()
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
console = Console()

BANNER = r"""
[bold cyan]
  ╔═╗╔═╗╦ ╦╔═╗╔╦╗╔═╗╔╦╗╦╔═╗  ╦╔═╗
  ╚═╗║  ╠═╣║╣ ║║║╠═╣ ║ ║║    ║║ ╣
  ╚═╝╚═╝╩ ╩╚═╝╩ ╩╩ ╩ ╩ ╩╚═╝  ╩╚═╝═
[/bold cyan]
[dim]  Electrical Schematic Extraction Pipeline (3-Stage)[/dim]
"""
console.print(Panel(BANNER, border_style="cyan", box=box.DOUBLE_EDGE, expand=False))


def parse_arguments():
    """Parse CLI arguments and return the image path."""
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        console.print("[bold red]Usage: python main.py <image_file>[/bold red]")
        raise SystemExit(1)
    image_path = args[0]
    if not os.path.isfile(image_path):
        console.print(f"[bold red]File not found:[/bold red] {image_path}")
        raise SystemExit(1)

    # Configure structured logging from --log-level / --json-log flags
    log_level = "WARNING"
    json_log = False
    pipeline_mode = None
    for a in sys.argv[1:]:
        if a.startswith("--log-level="):
            log_level = a.split("=", 1)[1]
        elif a == "--json-log":
            json_log = True
        elif a.startswith("--pipeline-mode="):
            mode_val = a.split("=", 1)[1].lower()
            pipeline_mode = PipelineMode(mode_val)
    configure_logging(level=log_level, json_output=json_log)

    return image_path


def initialize_foundry_service():
    """Authenticate and create the unified Foundry service."""
    with console.status("[bold yellow]Authenticating with Azure\u2026", spinner="dots"):
        service = FoundryService(console=console)
        # Eagerly verify OpenAI client connectivity
        service.get_openai_client()
    console.print("  [green]\u2714[/green] Azure clients ready\n")
    return service


# ══════════════════════════════════════════════════════════════════════════════
#  STAGE 1 — OpenCV Geometry Extraction
# ══════════════════════════════════════════════════════════════════════════════

def run_stage_1(image_path):
    """Execute Stage 1: deterministic OpenCV geometry extraction."""
    console.rule("[bold blue]STAGE 1 \u00b7 OpenCV Geometry Extraction[/bold blue]", style="blue")
    t0 = time.time()

    img_prefix = os.path.splitext(os.path.basename(image_path))[0]
    stage1_path = os.path.join("output", f"{img_prefix}-out-{timestamp}-stage1-geometry.json")

    with console.status("[bold blue]Extracting wire geometry with OpenCV\u2026", spinner="dots"):
        geometry = extract_geometry(image_path, output_path=stage1_path)
        wire_map = format_wire_map(geometry)

    elapsed = time.time() - t0
    summary = geometry["summary"]

    console.print(
        f"\n  [green]\u2714[/green] OpenCV found: "
        f"[bold]{summary['wires']}[/bold] wires "
        f"([bold]{summary['wire_chains']}[/bold] chains)  "
        f"[dim]({elapsed:.2f}s)[/dim]"
    )
    console.print(f"  [green]\u2714[/green] Stage 1 saved to [bold]{stage1_path}[/bold]\n")

    return geometry, wire_map, elapsed


# ══════════════════════════════════════════════════════════════════════════════
#  STAGE 2 — Diagram Discovery (LLM)
# ══════════════════════════════════════════════════════════════════════════════

def run_stage_2(foundry_service, image_data_b64, image_path, geometry, wire_map):
    """Execute Stage 2: multi-run LLM discovery with union merge."""
    console.rule(
        "[bold magenta]STAGE 2 \u00b7 Diagram Discovery[/bold magenta]",
        style="magenta",
    )

    img_prefix = os.path.splitext(os.path.basename(image_path))[0]
    stage2_path = os.path.join("output", f"{img_prefix}-out-{timestamp}-stage2-discovery.json")

    discovery, wire_map, elapsed = run_full_discovery(
        client=foundry_service.get_openai_client(),
        image_data_b64=image_data_b64,
        image_path=image_path,
        geometry=geometry,
        wire_map=wire_map,
        console=console,
        output_path=stage2_path,
    )

    return discovery, wire_map, elapsed


# ══════════════════════════════════════════════════════════════════════════════
#  STAGE 3 — Agent Extraction (Foundry Agent + Code Interpreter)
# ══════════════════════════════════════════════════════════════════════════════

def run_stage_3(foundry_service, image_path, geometry, discovery, wire_map):
    """Execute Stage 3: Foundry Agent extraction with Code Interpreter."""
    console.print()
    console.rule(
        "[bold cyan]STAGE 3 \u00b7 Foundry Agent + Code Interpreter[/bold cyan]",
        style="cyan",
    )
    console.print(f"  [dim]Agent writes & executes tailored OpenCV code per image[/dim]")
    console.print()

    parsed, elapsed = run_agent_extraction(
        image_path, geometry, discovery, wire_map, console, foundry_service
    )

    img_prefix = os.path.splitext(os.path.basename(image_path))[0]
    out_path = os.path.join("output", f"{img_prefix}-out-{timestamp}-stage3-final.json")

    parsed = post_process_and_validate(
        parsed, geometry, discovery, console, elapsed=elapsed, output_path=out_path
    )

    return parsed, elapsed


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Run the full 3-stage extraction pipeline."""
    image_path = parse_arguments()
    log = get_logger("pipeline")
    metrics = PipelineMetrics()

    log.info("pipeline_start", image=image_path)

    # Load image
    with console.status("[bold yellow]Loading image\u2026", spinner="dots"):
        with open(image_path, "rb") as f:
            image_data_b64 = base64.b64encode(f.read()).decode("utf-8")
    console.print(f"  [green]\u2714[/green] Image: [dim]{image_path}[/dim]\n")

    # Initialize unified Foundry service (OpenAI + Agent clients)
    foundry = initialize_foundry_service()

    # Stage 1: OpenCV Geometry Extraction
    with metrics.stage("stage1"):
        geometry, wire_map, elapsed_s1 = run_stage_1(image_path)
    summary = geometry.get("summary", {})
    metrics.set_counts(
        "stage1",
        wires=summary.get("wires", 0),
        wire_chains=summary.get("wire_chains", 0),
        dashed_regions=summary.get("dashed_regions", 0),
    )
    log.info(
        "stage1_done",
        elapsed=round(elapsed_s1, 3),
        **metrics.get_counts("stage1"),
    )

    # Stage 2: LLM Discovery
    with metrics.stage("stage2"):
        discovery, wire_map, elapsed_s2 = run_stage_2(
            foundry, image_data_b64, image_path, geometry, wire_map
        )
    metrics.set_counts(
        "stage2",
        components=len(discovery.get("components", [])),
        cables=len(discovery.get("cables", [])),
        terminals=len(discovery.get("terminals", [])),
    )
    log.info(
        "stage2_done",
        elapsed=round(elapsed_s2, 3),
        **metrics.get_counts("stage2"),
    )

    # Stage 3: Agent Extraction
    with metrics.stage("stage3"):
        final, elapsed_s3 = run_stage_3(foundry, image_path, geometry, discovery, wire_map)
    metrics.set_counts(
        "stage3",
        objects=len(final.get("objects", [])),
        connections=len(final.get("connections", [])),
    )
    log.info(
        "stage3_done",
        elapsed=round(elapsed_s3, 3),
        **metrics.get_counts("stage3"),
    )

    # Summary
    total_time = elapsed_s1 + elapsed_s2 + elapsed_s3
    console.print()
    console.print(
        Panel(
            f"[bold green]Pipeline complete[/bold green]  \u00b7  "
            f"[dim]S1 {elapsed_s1:.1f}s + S2 {elapsed_s2:.1f}s + S3 {elapsed_s3:.1f}s"
            f" = [/dim][bold]{total_time:.1f}s[/bold] total",
            border_style="green",
            box=box.DOUBLE_EDGE,
            expand=False,
        )
    )

    log.info("pipeline_done", **metrics.summary())


if __name__ == "__main__":
    try:
        main()
    except PipelineError as exc:
        console.print(f"\n[bold red]Pipeline failed:[/bold red] {exc}")
        log = get_logger("pipeline")
        log.error("pipeline_failed", error=str(exc), exit_code=exc.exit_code, **exc.details)
        raise SystemExit(exc.exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise SystemExit(130)
