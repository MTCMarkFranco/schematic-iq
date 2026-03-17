"""
Stage 2 Service — Diagram Discovery (LLM)

Uses a vision-capable LLM (gpt-4o-mini) to scan the schematic image and
produce an inventory of components, cables, terminals, wire labels, and
partition boundaries. Runs multiple passes and merges via union-dedup.
"""

import json
import os
import re
import time

from rich.console import Console
from rich.table import Table
from rich import box

DISCOVERY_RUNS_DEFAULT = 3
DISCOVERY_MAX_TOKENS_DEFAULT = 14_000


def run_discovery(client, model, image_data_b64, discovery_prompt, geometry,
                  num_runs=None, max_tokens=None, console=None, output_path=None):
    """Execute multi-run discovery and return merged discovery dict.

    Args:
        client: AzureOpenAI client instance.
        model: Deployment name for the mini/discovery model.
        image_data_b64: Base64-encoded image string.
        discovery_prompt: System prompt for discovery.
        geometry: Stage 1 geometry dict (for CV slider cross-reference).
        num_runs: Number of discovery runs (env: DISCOVERY_RUNS, default 3).
        max_tokens: Max completion tokens per run (env: DISCOVERY_MAX_TOKENS, default 14000).
        console: Rich Console for logging.
        output_path: Optional file path to save discovery JSON.

    Returns:
        (discovery_dict, elapsed_seconds).
    """
    if num_runs is None:
        num_runs = int(os.getenv("DISCOVERY_RUNS", DISCOVERY_RUNS_DEFAULT))
    if max_tokens is None:
        max_tokens = int(os.getenv("DISCOVERY_MAX_TOKENS", DISCOVERY_MAX_TOKENS_DEFAULT))
    if console is None:
        console = Console()

    console.print(f"  Model: [bold]{model}[/bold]  \u00d7{num_runs} runs \u2192 union merge")
    console.print()

    all_discoveries = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    t0 = time.time()
    for run_idx in range(num_runs):
        with console.status(
            f"[bold magenta]Run {run_idx + 1}/{num_runs} \u2014 scanning with {model}\u2026",
            spinner="dots12",
            spinner_style="magenta",
        ):
            resp = client.chat.completions.create(
                model=model,
                temperature=0.8,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": discovery_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_data_b64}", "detail": "high"},
                            },
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=max_tokens,
            )
        content = resp.choices[0].message.content
        finish = resp.choices[0].finish_reason
        if content:
            if finish == "length":
                console.print(f"  Run {run_idx + 1}: [yellow]truncated \u2014 skipping[/yellow]")
                continue
            try:
                d = json.loads(content)
            except json.JSONDecodeError as e:
                console.print(f"  Run {run_idx + 1}: [red]malformed JSON ({e.msg}) \u2014 skipping[/red]")
                continue
            all_discoveries.append(d)
            total_prompt_tokens += resp.usage.prompt_tokens
            total_completion_tokens += resp.usage.completion_tokens

            run_comps = [_label(c) for c in d.get("components", [])]
            run_cables = [_label(c) for c in d.get("cables", [])]
            run_terms = [_label(t) for t in d.get("terminals", [])]
            run_parts = d.get("partition_labels", [])
            console.print(
                f"  Run {run_idx + 1}: {len(run_comps)} components [{', '.join(run_comps)}]  "
                f"{len(run_cables)} cables [{', '.join(run_cables)}]  "
                f"{len(run_terms)} terminals  "
                f"{len(run_parts)} partitions [{', '.join(run_parts)}]"
            )
        else:
            console.print(f"  Run {run_idx + 1}: [red]empty response[/red]")

    elapsed = time.time() - t0

    if not all_discoveries:
        raise RuntimeError("Discovery failed \u2014 all runs returned empty")

    discovery = _merge_discoveries(all_discoveries)

    # Enforce schema: terminals must not carry wire label ownership fields
    for t in discovery["terminals"]:
        if isinstance(t, dict):
            t.pop("nearby_wire_labels", None)
            t.pop("left_label", None)
            t.pop("right_label", None)

    # Cross-reference CV slider detections with terminal labels
    cv_slider_labels = _match_cv_sliders_to_terminals(geometry, discovery["terminals"])
    if cv_slider_labels:
        for t in discovery["terminals"]:
            if isinstance(t, dict) and t.get("label", "") in cv_slider_labels:
                t["has_slider"] = True
        console.print(
            f"  [green]\u2714[/green] CV slider override: has_slider=true on "
            f"{', '.join(sorted(cv_slider_labels))}"
        )

    # Build summary table
    comp_labels = [_label(c) for c in discovery["components"]]
    cable_labels = [_label(c) for c in discovery["cables"]]
    term_labels = [_label(t) for t in discovery["terminals"]]
    wire_list = discovery["wire_labels"]
    other_list = discovery["other_symbols"]
    part_list = discovery["partition_labels"]

    tbl = Table(box=box.ROUNDED, border_style="magenta", show_header=False, padding=(0, 2))
    tbl.add_column("Category", style="bold")
    tbl.add_column("Count", justify="right", style="bold magenta")
    tbl.add_column("Items", style="dim")
    tbl.add_row("Components", str(len(discovery["components"])),
                ", ".join(comp_labels) if comp_labels else "\u2014")
    tbl.add_row("Cables", str(len(discovery["cables"])),
                ", ".join(cable_labels) if cable_labels else "\u2014")
    tbl.add_row("Terminals", str(len(discovery["terminals"])),
                ", ".join(term_labels) if term_labels else "\u2014")
    tbl.add_row("Wire Labels", str(len(wire_list)),
                ", ".join(wire_list) if wire_list else "\u2014")
    tbl.add_row("Other Symbols", str(len(other_list)),
                ", ".join(_label(s) for s in other_list) if other_list else "\u2014")
    tbl.add_row("Partitions", str(len(part_list)),
                ", ".join(part_list) if part_list else "\u2014")
    tbl.add_row("Crossovers", "Yes" if discovery["has_crossovers"] else "No", "")

    console.print()
    console.print(tbl)
    console.print(
        f"\n  [green]\u2714[/green] Discovery complete in [bold]{elapsed:.1f}s[/bold]  "
        f"[dim]tokens: {total_prompt_tokens + total_completion_tokens:,}[/dim]"
    )
    if discovery.get("notes"):
        console.print(f"  [dim italic]Notes: {discovery['notes']}[/dim italic]")

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(discovery, f, indent=2)

    return discovery, elapsed


def run_full_discovery(client, image_data_b64, image_path, geometry, wire_map,
                      console=None, output_path=None):
    """Full Stage 2 pipeline: discovery + wire map supplements.

    Loads the discovery prompt, runs multi-pass discovery, computes cable
    routing and terminal wire supplements, and appends them to wire_map.

    Returns (discovery, updated_wire_map, elapsed).
    """
    if console is None:
        console = Console()

    model = os.getenv("AZURE_OPENAI_MINI_DEPLOYMENT", "gpt-4o-mini")
    prompt_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
    with open(os.path.join(prompt_dir, "system-prompt-discovery.md"), "r", encoding="utf-8") as f:
        discovery_prompt = f.read()

    discovery, elapsed = run_discovery(
        client=client,
        model=model,
        image_data_b64=image_data_b64,
        discovery_prompt=discovery_prompt,
        geometry=geometry,
        console=console,
        output_path=output_path,
    )

    # Compute supplementary wire map data
    cable_list = discovery["cables"]
    term_list = discovery["terminals"]

    cable_routing_map, terminal_wire_info, wire_map_supplement = build_wire_map_supplements(
        geometry, image_path, cable_list, term_list
    )
    wire_map += wire_map_supplement

    if cable_routing_map and cable_routing_map.get("routing"):
        cable_circles = cable_routing_map.get("cable_circles", [])
        console.print(f"  [green]\u2714[/green] Cable routing map: {len(cable_circles)} cable circles")
    else:
        console.print(f"  [dim]\u2139  Cable routing map not available[/dim]")

    if terminal_wire_info and terminal_wire_info.get("jumper_pairs"):
        jp = terminal_wire_info["jumper_pairs"]
        console.print(f"  [green]\u2714[/green] Terminal wire analysis: {len(jp)} jumper pairs")
        for wired, jumpered in jp:
            console.print(f"      {wired} \u2190JUMPER\u2192 {jumpered}")
    else:
        console.print(f"  [dim]\u2139  No jumper pairs detected[/dim]")

    return discovery, wire_map, elapsed


def _label(item):
    """Extract label string from a dict-or-string discovery item."""
    if isinstance(item, dict):
        return item.get("label", item.get("text", str(item)))
    return str(item)


def _merge_discoveries(all_discoveries):
    """Union-merge multiple discovery runs, deduplicated by label."""
    merged_comps = {}
    merged_cables = {}
    merged_terminals = {}
    merged_wires = set()
    merged_others = {}
    merged_parts = set()
    has_crossovers = False

    for d in all_discoveries:
        for c in d.get("components", []):
            lbl = _label(c)
            if lbl not in merged_comps:
                merged_comps[lbl] = c
        for c in d.get("cables", []):
            lbl = _label(c)
            if lbl not in merged_cables:
                merged_cables[lbl] = c
        for t in d.get("terminals", []):
            lbl = _label(t)
            if lbl not in merged_terminals:
                merged_terminals[lbl] = t
        for w in d.get("wire_labels", []):
            merged_wires.add(w)
        for s in d.get("other_symbols", []):
            lbl = s.get("text", s) if isinstance(s, dict) else s
            if lbl not in merged_others:
                merged_others[lbl] = s
        for p in d.get("partition_labels", []):
            merged_parts.add(p)
        if d.get("has_crossovers"):
            has_crossovers = True

    return {
        "components": list(merged_comps.values()),
        "cables": list(merged_cables.values()),
        "terminals": list(merged_terminals.values()),
        "wire_labels": sorted(merged_wires),
        "other_symbols": list(merged_others.values()),
        "partition_labels": sorted(merged_parts),
        "has_crossovers": has_crossovers,
        "notes": all_discoveries[0].get("notes", ""),
    }


def _match_cv_sliders_to_terminals(geometry, terminals):
    """Cross-reference CV-detected slider rects with terminal list.
    Returns set of terminal label strings that should have has_slider=True."""
    slider_rects = geometry.get("slider_rects", [])
    dashed_regions = geometry.get("dashed_regions", [])
    if not slider_rects or not dashed_regions:
        return set()

    numeric_labels = []
    for t in terminals:
        label = t["label"] if isinstance(t, dict) else t
        if str(label).isdigit():
            numeric_labels.append(int(label))
    numeric_labels.sort(reverse=True)
    if not numeric_labels:
        return set()

    groups = [[numeric_labels[0]]]
    for i in range(1, len(numeric_labels)):
        if groups[-1][-1] - numeric_labels[i] > 50:
            groups.append([numeric_labels[i]])
        else:
            groups[-1].append(numeric_labels[i])

    slider_labels = set()
    for sr in slider_rects:
        sx, sy, sh = sr["x"], sr["y"], sr["height"]
        slider_cy = sy + sh / 2

        containing = None
        for dr in dashed_regions:
            if (dr["x"] <= sx <= dr["x"] + dr["width"]
                    and dr["y"] <= sy <= dr["y"] + dr["height"]
                    and dr["height"] > 10):
                area = dr["width"] * dr["height"]
                if containing is None or area < containing["width"] * containing["height"]:
                    containing = dr
        if containing is None or containing["height"] <= 0:
            continue

        target_group = max(groups, key=len)
        n = len(target_group)
        frac = (slider_cy - containing["y"]) / containing["height"]
        idx = min(max(round(frac * n - 0.5), 0), n - 1)
        slider_labels.add(str(target_group[idx]))

    return slider_labels


def build_wire_map_supplements(geometry, image_path, cable_list, term_list):
    """Compute cable routing map and terminal wire analysis, returning
    (cable_routing_map, terminal_wire_info, wire_map_supplement) tuple."""
    from services.geometry_extraction_service import (
        compute_cable_routing_map,
        analyze_terminal_wires,
    )

    wire_map_supplement = ""

    cable_routing_map = compute_cable_routing_map(image_path, geometry, cable_list)
    if cable_routing_map and cable_routing_map.get("routing"):
        cable_circles = cable_routing_map.get("cable_circles", [])
        routing_lines = [
            "",
            "    Cable circles detected at (informational):",
        ]
        for cc in cable_circles:
            routing_lines.append(f"      {cc['label']}: center y\u2248{cc['y']} (radius={cc['r']}px)")
        routing_lines.append("")
        wire_map_supplement += "\n" + "\n".join(routing_lines)

    terminal_wire_info = analyze_terminal_wires(image_path, geometry, term_list)
    if terminal_wire_info and terminal_wire_info.get("jumper_pairs"):
        jp = terminal_wire_info["jumper_pairs"]
        ti = terminal_wire_info["terminal_info"]

        tw_lines = [
            "",
            "\u26a0\ufe0f  TERMINAL WIRE ANALYSIS (OpenCV \u2014 AUTHORITATIVE)",
            "    Some terminals have a cable wire going RIGHT from the terminal block.",
            "    Terminals WITHOUT a right-side wire connect via a JUMPER.",
            "",
            "    DETECTED JUMPER PAIRS (wired \u2192 jumpered):",
        ]
        for wired, jumpered in jp:
            tw_lines.append(f"      {wired} (has cable wire) \u2190JUMPER\u2192 {jumpered} (no direct cable wire)")
        tw_lines.append("")
        tw_lines.append("    TERMINALS WITHOUT RIGHT-SIDE WIRE:")
        for t in ti:
            if not t["has_right_wire"]:
                partner = t["jumper_partner"] or "unknown"
                tw_lines.append(f"      {t['label']}: NO right-side wire \u2192 jumpered to {partner}")
        tw_lines.append("")
        tw_lines.append("    CROSS-CONNECTION RULE: Jumpered terminal routes to a DIFFERENT cable")
        tw_lines.append("    than its wired partner. Trace independently through the bus.")
        tw_lines.append("")

        wire_map_supplement += "\n" + "\n".join(tw_lines)
    else:
        terminal_wire_info = {}

    return cable_routing_map, terminal_wire_info, wire_map_supplement
