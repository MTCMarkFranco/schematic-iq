"""
Validation Service — Shared Post-Processing Utilities

Provides extraction normalization, structural graph validation,
cable label cleanup, and discovery cross-checking across all stages.
"""

import os
import re
import json

from rich.table import Table
from rich import box


def save_output(data, output_path):
    """Save a dict as JSON to the given path, creating directories as needed."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)


def post_process_and_validate(parsed, geometry, discovery, console,
                              elapsed=None, output_path=None):
    """Full post-processing: normalize, validate, cross-check, slider enforcement, save.

    Returns the processed extraction dict.
    """
    parsed = normalize_extraction(parsed)
    parsed = normalize_cable_labels(parsed)

    n_objects = len(parsed.get("objects", []))
    n_connections = len(parsed.get("connections", []))
    n_wires = sum(1 for o in parsed.get("objects", []) if o.get("object_type") == "WIRE")
    n_jumpers = sum(1 for c in parsed.get("connections", []) if c.get("relationship_type") == "JUMPER_SHORT")

    tbl = Table(box=box.ROUNDED, border_style="cyan", show_header=False, padding=(0, 2))
    tbl.add_column("Metric", style="bold")
    tbl.add_column("Value", justify="right", style="bold cyan")
    tbl.add_row("Objects", str(n_objects))
    tbl.add_row("Connections", str(n_connections))
    tbl.add_row("Wires", str(n_wires))
    tbl.add_row("Jumper pairs", str(n_jumpers))
    if elapsed is not None:
        tbl.add_row("Time", f"{elapsed:.1f}s")
    console.print()
    console.print(tbl)

    # Structural validation
    issues = validate_graph(parsed, geometry=geometry)
    if issues:
        console.print(f"\n  [yellow]\u26a0[/yellow] {len(issues)} structural issues:")
        for i, issue in enumerate(issues, 1):
            console.print(f"    {i}. [yellow]{issue}[/yellow]")
    else:
        console.print(f"\n  [green]\u2714[/green] All structural checks pass")

    # Discovery cross-check
    disc_missing = discovery_cross_check(parsed, discovery)
    if disc_missing:
        console.print(f"\n  [yellow]\u26a0[/yellow] {len(disc_missing)} discovery items missing:")
        for m in disc_missing:
            console.print(f"    - [yellow]{m}[/yellow]")
    else:
        console.print(f"\n  [green]\u2714[/green] All discovery items present")

    # CV slider enforcement
    cv_slider_labels = set()
    for t in discovery.get("terminals", []):
        if isinstance(t, dict) and t.get("has_slider"):
            cv_slider_labels.add(t["label"])

    for obj in parsed.get("objects", []):
        if obj.get("object_type") != "TERMINAL":
            continue
        label = obj.get("raw_text", "")
        if label in cv_slider_labels:
            if not obj.get("has_slider"):
                obj["has_slider"] = True
                console.print(
                    f"  [green]\u2714[/green] Forced has_slider=true on "
                    f"{obj['system_object_id']} ('{label}')"
                )
        else:
            if obj.get("has_slider"):
                console.print(
                    f"  [yellow]\u26a0[/yellow] Cleared hallucinated has_slider on "
                    f"{obj['system_object_id']} ('{label}')"
                )
                obj["has_slider"] = False

    if output_path:
        save_output(parsed, output_path)
        console.print(f"\n  [green]\u2714[/green] Final output written to [bold]{output_path}[/bold]")

    return parsed


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
#  EXTRACTION NORMALIZATION
# ────────────────────────────────────────────────────────────────────────────

def normalize_extraction(data):
    """Normalize model response to expected schema (objects, connections, partition_memberships)."""
    if "objects" not in data:
        for val in data.values():
            if isinstance(val, dict) and "objects" in val:
                data = val
                break

    if "relationships" in data and "connections" not in data:
        data["connections"] = data.pop("relationships")

    data.setdefault("objects", [])
    data.setdefault("connections", [])
    data.setdefault("partition_memberships", [])

    cleaned_objects = []
    for idx, o in enumerate(data["objects"]):
        if not isinstance(o, dict):
            continue
        if "system_object_id" not in o:
            for alt in ("id", "object_id", "obj_id", "system_id"):
                if alt in o:
                    o["system_object_id"] = o[alt]
                    break
            else:
                o["system_object_id"] = f"OBJ_REPAIR_{idx}"
        if "object_type" not in o:
            vf = o.get("visual_form", "").lower()
            if "line" in vf:
                o["object_type"] = "WIRE"
            elif "circle" in vf:
                o["object_type"] = "OFF_PAGE_CONNECTOR"
            elif "rectangle" in vf or "rect" in vf:
                o["object_type"] = "TERMINAL"
            else:
                o["object_type"] = "LABEL"
        o.setdefault("visual_form", "unknown")
        o.setdefault("raw_text", "")
        o.setdefault("confidence_score", 0.0)
        cleaned_objects.append(o)
    data["objects"] = cleaned_objects

    cleaned_conns = []
    for idx, c in enumerate(data["connections"]):
        if not isinstance(c, dict):
            continue
        c.setdefault("connection_id", f"C_REPAIR_{idx}")
        c.setdefault("source_object_id", "")
        c.setdefault("target_object_id", "")
        c.setdefault("relationship_type", "UNRESOLVED")
        cleaned_conns.append(c)
    data["connections"] = cleaned_conns

    return data


def normalize_cable_labels(data):
    """Clean cable label text: strip conductor-count suffix, normalize whitespace, merge duplicates."""
    objects = data.get("objects", [])
    conns = data.get("connections", [])

    for obj in objects:
        if obj.get("object_type") in ("CABLE", "CABLE_LABEL"):
            cleaned = re.sub(r'\s+\d+C$', '', obj["raw_text"].strip())
            if cleaned:
                cleaned = re.sub(r'\s+', '', cleaned)
                obj["raw_text"] = cleaned

    pure_cc = {obj["system_object_id"] for obj in objects
               if obj.get("object_type") in ("CABLE", "CABLE_LABEL")
               and re.match(r'^\d+C$', obj["raw_text"].strip())}
    if pure_cc:
        conns[:] = [c for c in conns
                    if c["source_object_id"] not in pure_cc
                    and c["target_object_id"] not in pure_cc]
        objects[:] = [o for o in objects if o["system_object_id"] not in pure_cc]

    cable_groups = {}
    for obj in objects:
        if obj.get("object_type") in ("CABLE", "CABLE_LABEL"):
            cable_groups.setdefault(obj["raw_text"].strip(), []).append(obj["system_object_id"])

    merge_ids = set()
    for text, oid_list in cable_groups.items():
        if len(oid_list) <= 1:
            continue
        keep = oid_list[0]
        for dup in oid_list[1:]:
            merge_ids.add(dup)
            for c in conns:
                if c["source_object_id"] == dup:
                    c["source_object_id"] = keep
                if c["target_object_id"] == dup:
                    c["target_object_id"] = keep
    if merge_ids:
        objects[:] = [o for o in objects if o["system_object_id"] not in merge_ids]

    seen = set()
    deduped = []
    for c in conns:
        key = (c["source_object_id"], c["target_object_id"], c["relationship_type"])
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    conns[:] = deduped

    return data


# ────────────────────────────────────────────────────────────────────────────
#  STRUCTURAL GRAPH VALIDATION
# ────────────────────────────────────────────────────────────────────────────

def validate_graph(data, geometry=None):
    """Run structural checks on extraction JSON, return list of issue strings."""
    issues = []

    def flatten(arr):
        flat = []
        for item in arr:
            if isinstance(item, list):
                flat.extend(flatten(item))
            elif isinstance(item, dict):
                flat.append(item)
        return flat

    raw_objects = data.get("objects", [])
    if raw_objects and isinstance(raw_objects[0], list):
        raw_objects = flatten(raw_objects)
        data["objects"] = raw_objects

    for o in raw_objects:
        if "system_object_id" not in o:
            for alt in ("id", "object_id", "obj_id", "system_id"):
                if alt in o:
                    o["system_object_id"] = o[alt]
                    break
            else:
                o["system_object_id"] = f"OBJ_UNKNOWN_{raw_objects.index(o)}"

    raw_conns = data.get("connections", data.get("relationships", []))
    if raw_conns and isinstance(raw_conns[0], list):
        raw_conns = flatten(raw_conns)
        data["connections"] = raw_conns

    # Auto-remove phantom wires
    conn_list_tmp = data.get("connections", data.get("relationships", []))
    connected_ids = set()
    for c in conn_list_tmp:
        connected_ids.add(c.get("source_object_id", c.get("source", "")))
        connected_ids.add(c.get("target_object_id", c.get("target", "")))
    before_count = len(raw_objects)
    raw_objects = [
        o for o in raw_objects
        if not (
            o.get("object_type") == "WIRE"
            and not o.get("raw_text", "").strip()
            and o["system_object_id"] not in connected_ids
        )
    ]
    if len(raw_objects) < before_count:
        data["objects"] = raw_objects

    objects = {o["system_object_id"]: o for o in raw_objects}
    connections = data.get("connections", data.get("relationships", []))

    for c in connections:
        if "source" in c and "source_object_id" not in c:
            c["source_object_id"] = c["source"]
        if "target" in c and "target_object_id" not in c:
            c["target_object_id"] = c["target"]
        if "type" in c and "relationship_type" not in c:
            c["relationship_type"] = c["type"]

    obj_connections = {oid: [] for oid in objects}
    for c in connections:
        src = c.get("source_object_id", "")
        tgt = c.get("target_object_id", "")
        if src in obj_connections:
            obj_connections[src].append(c)
        if tgt in obj_connections:
            obj_connections[tgt].append(c)

    # Check 1: Orphaned objects
    for oid, obj in objects.items():
        if obj["object_type"] in ("LABEL", "EXTERNAL_REF", "TERMINAL"):
            continue
        if not obj_connections[oid]:
            issues.append(
                f"ORPHAN: {oid} ({obj['object_type']} '{obj['raw_text']}') has ZERO connections"
            )

    # Check 2: TERMINAL PIN_OF
    terminals = [o for o in objects.values() if o["object_type"] == "TERMINAL"]
    has_components = any(o["object_type"] == "SYMBOLIC_COMPONENT" for o in objects.values())

    def _is_component_pin_terminal(raw_text):
        txt = str(raw_text or "").strip()
        if not txt:
            return False
        if "(" in txt or ")" in txt:
            return True
        return bool(re.search(r"^[A-Z]{1,3}(?:/[A-Z]{1,3})?$", txt, re.IGNORECASE))

    for t in terminals:
        tid = t["system_object_id"]
        if not has_components or not _is_component_pin_terminal(t.get("raw_text", "")):
            continue
        has_pin_of = any(
            c["relationship_type"] == "PIN_OF"
            and (c["source_object_id"] == tid or c["target_object_id"] == tid)
            for c in connections
        )
        if not has_pin_of:
            issues.append(
                f"MISSING PIN_OF: Terminal {tid} ('{t['raw_text']}') has no PIN_OF to any component"
            )

    # Check 3: WIRE completeness
    wires = [o for o in objects.values() if o["object_type"] == "WIRE"]
    for w in wires:
        wid = w["system_object_id"]
        wire_conns = [c for c in connections if c["source_object_id"] == wid or c["target_object_id"] == wid]
        if len(wire_conns) < 2:
            issues.append(
                f"INCOMPLETE WIRE: {wid} ('{w['raw_text']}') has only {len(wire_conns)} connection(s)"
            )

    # Check 4: OFF_PAGE_CONNECTOR reachability
    opc_ids = [
        o["system_object_id"] for o in objects.values()
        if o["object_type"] == "OFF_PAGE_CONNECTOR"
        and o.get("visual_form", "") not in ("pentagon", "arrow")
    ]
    for oid in opc_ids:
        has_cable = any(
            c["relationship_type"] == "CABLE_TO_CONNECTOR"
            and (c["source_object_id"] == oid or c["target_object_id"] == oid)
            for c in connections
        )
        if not has_cable:
            issues.append(
                f"UNREACHABLE CONNECTOR: {oid} ('{objects[oid]['raw_text']}') has no CABLE_TO_CONNECTOR"
            )

    # Check 5: Interleaved cable misrouting
    cable_labels = {oid: obj for oid, obj in objects.items() if obj["object_type"] == "CABLE_LABEL"}
    if len(cable_labels) >= 2:
        wire_to_cable = {}
        for c in connections:
            if c.get("relationship_type") == "WIRE_TO_CABLE":
                wire_to_cable[c.get("source_object_id", "")] = c.get("target_object_id", "")
        terminal_to_cable = {}
        for c in connections:
            if c.get("relationship_type") == "DIRECT_WIRE":
                src = objects.get(c.get("source_object_id", ""), {})
                tgt = objects.get(c.get("target_object_id", ""), {})
                if src.get("object_type") == "TERMINAL" and c.get("target_object_id") in wire_to_cable:
                    terminal_to_cable[c["source_object_id"]] = wire_to_cable[c["target_object_id"]]
                elif tgt.get("object_type") == "TERMINAL" and c.get("source_object_id") in wire_to_cable:
                    terminal_to_cable[c["target_object_id"]] = wire_to_cable[c["source_object_id"]]

        cable_terminal_counts = {cid: 0 for cid in cable_labels}
        for tid, cid in terminal_to_cable.items():
            if cid in cable_terminal_counts:
                cable_terminal_counts[cid] += 1
        starved = [cid for cid, cnt in cable_terminal_counts.items() if cnt == 0]
        overloaded = [cid for cid, cnt in cable_terminal_counts.items() if cnt > 0]
        if starved and overloaded:
            for cid in starved:
                cable_text = cable_labels[cid].get("raw_text", "?")
                issues.append(
                    f"INTERLEAVE SUSPECT: Cable '{cable_text}' ({cid}) has ZERO terminal connections"
                )

    # Check 6: CV slider mismatch
    slider_rects = (geometry or {}).get("slider_rects", [])
    if slider_rects:
        slider_terminal_ids = [
            t["system_object_id"] for t in terminals if t.get("has_slider") is True
        ]
        if not slider_terminal_ids:
            coords = "; ".join(
                f"({sr['x']},{sr['y']}) {sr['width']}\u00d7{sr['height']}px"
                for sr in slider_rects
            )
            issues.append(
                f"SLIDER MISMATCH: OpenCV detected {len(slider_rects)} slider(s) at [{coords}] "
                f"but no terminal has has_slider=true"
            )

    # Check 7: Numeric wire labels
    for oid, obj in objects.items():
        if obj["object_type"] != "WIRE":
            continue
        wire_text = obj.get("raw_text", "").strip()
        if wire_text and wire_text.isdigit():
            issues.append(
                f"NUMERIC WIRE LABEL: {oid} ('{wire_text}') \u2014 numeric labels are drafter refs, not wire IDs"
            )

    # Check 8: Conductor-count label objects
    for oid, obj in objects.items():
        raw = obj.get("raw_text", "").strip()
        if re.match(r'^\d+C$', raw, re.IGNORECASE):
            issues.append(
                f"CONDUCTOR-COUNT LABEL: {oid} ('{raw}') \u2014 remove this object and its connections"
            )

    return issues


# ────────────────────────────────────────────────────────────────────────────
#  DISCOVERY CROSS-CHECK
# ────────────────────────────────────────────────────────────────────────────

def discovery_cross_check(final_data, discovery_data):
    """Verify all discovery items appear in final output. Returns list of missing items."""
    missing = []
    final_texts = {o.get("raw_text", "").strip() for o in final_data.get("objects", [])}

    for comp in discovery_data.get("components", []):
        label = comp["label"] if isinstance(comp, dict) else comp
        if not any(label in t for t in final_texts):
            missing.append(f"COMPONENT '{label}' from discovery not found")

    for cable in discovery_data.get("cables", []):
        label = cable["label"] if isinstance(cable, dict) else cable
        if not any(label in t for t in final_texts):
            missing.append(f"CABLE '{label}' from discovery not found")

    for term in discovery_data.get("terminals", []):
        label = term["label"] if isinstance(term, dict) else term
        if label not in final_texts:
            missing.append(f"TERMINAL '{label}' from discovery not found")

    return missing
