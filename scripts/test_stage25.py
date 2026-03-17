#!/usr/bin/env python
"""Test the Stage 2.5 deterministic wire connection builder in isolation."""

import json
import sys


def build_deterministic_connections(parsed, geometry, cable_routing_map, image_path):
    """Copy of the function from main.py for standalone testing."""
    from cv_preprocess import detect_terminal_rects, load_binary_image, batch_analyze_intersections

    WIRE_COLORS = ["R", "W", "B", "BK"]

    objects = list(parsed.get("objects", []))
    connections = list(parsed.get("connections", []))
    partitions = list(parsed.get("partition_memberships", []))

    # Strip existing LLM-generated wire data
    wire_ids = {o["system_object_id"] for o in objects if o.get("object_type") == "WIRE"}
    objects = [o for o in objects if o.get("object_type") != "WIRE"]
    connections = [c for c in connections
                   if c.get("relationship_type") not in
                   ("DIRECT_WIRE", "WIRE_TO_CABLE", "JUMPER_SHORT")]
    partitions = [p for p in partitions if p.get("member_object_id") not in wire_ids]

    terminals = [o for o in objects if o.get("object_type") == "TERMINAL"]
    cables_objs = [o for o in objects if o.get("object_type") == "CABLE_LABEL"]

    term_by_label = {}
    for t in terminals:
        lbl = t["raw_text"].strip()
        term_by_label[lbl] = t

    cable_by_label = {}
    for c in cables_objs:
        lbl = c["raw_text"].strip().replace(" ", "")
        cable_by_label[lbl] = c

    cable_circles = cable_routing_map.get("cable_circles", [])
    cable_y = {}
    for cc in cable_circles:
        lbl = cc["label"].replace(" ", "")
        cable_y[lbl] = cc["y"]
    sorted_cables = sorted(cable_y.items(), key=lambda kv: kv[1])

    _, binary = load_binary_image(image_path)
    scale = geometry.get("scale", 1.0)
    term_rects = sorted(detect_terminal_rects(binary, scale), key=lambda r: r["cy"])

    # Find largest y-gap to split terminal groups
    if len(term_rects) >= 2:
        gaps = [(term_rects[i]["cy"] - term_rects[i - 1]["cy"], i)
                for i in range(1, len(term_rects))]
        gaps.sort(reverse=True)
        median_gap = sorted(g for g, _ in gaps)[len(gaps) // 2]
        if gaps[0][0] > median_gap * 3:
            split_idx = gaps[0][1]
        else:
            split_idx = 0
    else:
        split_idx = 0

    top_rects = term_rects[:split_idx]
    main_rects = term_rects[split_idx:]

    numeric_labels = []
    for t in terminals:
        lbl = t["raw_text"].strip()
        if lbl.isdigit():
            numeric_labels.append((int(lbl), lbl))
    numeric_labels.sort(reverse=True)

    if not numeric_labels:
        return parsed

    label_gaps = []
    for i in range(1, len(numeric_labels)):
        gap = numeric_labels[i - 1][0] - numeric_labels[i][0]
        label_gaps.append((gap, i))
    label_gaps.sort(reverse=True)

    if label_gaps and label_gaps[0][0] > 100:
        label_split = label_gaps[0][1]
        main_labels = [lbl for _, lbl in numeric_labels[:label_split]]
        top_labels = [lbl for _, lbl in numeric_labels[label_split:]]
    else:
        main_labels = [lbl for _, lbl in numeric_labels]
        top_labels = []

    print(f"  Top group ({len(top_labels)}): {top_labels}")
    print(f"  Main group ({len(main_labels)}): {main_labels}")
    print(f"  Top rects: {len(top_rects)}, Main rects: {len(main_rects)}")
    print(f"  Cables sorted by y: {sorted_cables}")

    if top_labels and len(sorted_cables) >= 1:
        top_cable_label = sorted_cables[0][0]
        main_cable_labels = [lbl for lbl, _ in sorted_cables[1:]]
    else:
        top_cable_label = None
        main_cable_labels = [lbl for lbl, _ in sorted_cables]

    print(f"  Top cable: {top_cable_label}")
    print(f"  Main cables: {main_cable_labels}")

    # Bus lines
    v_wires = [w for w in geometry.get("wires", []) if w.get("orientation") == "vertical"]
    if v_wires:
        max_vlen = max(w["length"] for w in v_wires)
        bus_lines = sorted(
            [w for w in v_wires if w["length"] >= max_vlen * 0.85],
            key=lambda w: w["x1"],
        )
    else:
        bus_lines = []

    if len(bus_lines) >= 4:
        bus_C = bus_lines[2]
    elif len(bus_lines) >= 2:
        bus_C = bus_lines[-1]
    else:
        bus_C = None

    print(f"  Bus lines: {len(bus_lines)}")
    if bus_C:
        print(f"  Bus C: x={bus_C['x1']}")

    h_wires = sorted(
        [w for w in geometry.get("wires", []) if w.get("orientation") == "horizontal"],
        key=lambda w: w["y1"],
    )

    wired_terminals_set = set()

    if bus_C and main_rects:
        main_y_lo = main_rects[0]["cy"] - 40
        main_y_hi = main_rects[-1]["cy"] + 40
        right_wires_main = [
            w for w in h_wires
            if w["x1"] >= 600 and w["y1"] >= main_y_lo and w["y1"] <= main_y_hi
        ]

        # Match each terminal rect to its right-side wire.
        # Wire exits the UPPER portion of the terminal: cy - 45 < wy < cy - 5
        for i, rect in enumerate(main_rects):
            if i >= len(main_labels):
                break
            cy = rect["cy"]
            best_wire = None
            best_offset = 999
            for rw in right_wires_main:
                offset = cy - rw["y1"]
                if 5 < offset < 45 and offset < best_offset:
                    best_offset = offset
                    best_wire = rw
            if best_wire is None:
                continue
            results = batch_analyze_intersections(binary, best_wire["y1"], [bus_C], scale)
            if results and results[0].get("verdict") == "BEND":
                wired_terminals_set.add(main_labels[i])

    print(f"  Wired terminals (bus C BEND): {sorted(wired_terminals_set, reverse=True)}")

    main_pairs = []
    for i in range(0, len(main_labels) - 1, 2):
        main_pairs.append((main_labels[i], main_labels[i + 1]))
    if len(main_labels) % 2 == 1:
        main_pairs.append((main_labels[-1], None))

    wired_main = []
    for pair_idx, (a, b) in enumerate(main_pairs):
        if b is None:
            wired_main.append((a, None))
            continue
        a_wired = a in wired_terminals_set
        b_wired = b in wired_terminals_set
        if a_wired and not b_wired:
            wired_main.append((a, b))
        elif b_wired and not a_wired:
            wired_main.append((b, a))
        else:
            if pair_idx % 2 == 0:
                wired_main.append((a, b))
            else:
                wired_main.append((b, a))

    print(f"\n  Pairs (wired, jumpered):")
    for i, (w, j) in enumerate(wired_main):
        print(f"    Pair {i}: {w} (wired) / {j} (jumpered)")

    if len(main_cable_labels) >= 2:
        closer_cable = main_cable_labels[0]
        farther_cable = main_cable_labels[1]
    elif len(main_cable_labels) == 1:
        closer_cable = main_cable_labels[0]
        farther_cable = main_cable_labels[0]
    else:
        closer_cable = None
        farther_cable = None

    obj_counter = max(
        (int(o["system_object_id"].replace("OBJ", ""))
         for o in objects if o["system_object_id"].startswith("OBJ")),
        default=0,
    ) + 1
    conn_counter = max(
        (int(c["connection_id"].replace("C", ""))
         for c in connections if c["connection_id"].startswith("C")),
        default=0,
    ) + 1

    new_objects = list(objects)
    new_connections = list(connections)
    new_partitions = list(partitions)

    partition_id = None
    for p in partitions:
        for t in terminals:
            if p.get("member_object_id") == t["system_object_id"]:
                partition_id = p.get("partition_id")
                break
        if partition_id:
            break

    def add_wire(terminal_label, cable_label, wire_color):
        nonlocal obj_counter, conn_counter
        term_obj = term_by_label.get(terminal_label)
        cable_obj = cable_by_label.get(cable_label)
        if not term_obj or not cable_obj:
            print(f"  WARNING: missing term={terminal_label} or cable={cable_label}")
            return
        wire_id = f"OBJ{obj_counter}"
        obj_counter += 1
        new_objects.append({
            "system_object_id": wire_id,
            "object_type": "WIRE",
            "visual_form": "line",
            "raw_text": wire_color,
            "confidence_score": 0.95,
        })
        cid1 = f"C{conn_counter}"
        conn_counter += 1
        new_connections.append({
            "connection_id": cid1,
            "source_object_id": term_obj["system_object_id"],
            "target_object_id": wire_id,
            "relationship_type": "DIRECT_WIRE",
        })
        cid2 = f"C{conn_counter}"
        conn_counter += 1
        new_connections.append({
            "connection_id": cid2,
            "source_object_id": wire_id,
            "target_object_id": cable_obj["system_object_id"],
            "relationship_type": "WIRE_TO_CABLE",
        })
        if partition_id:
            new_partitions.append({"partition_id": partition_id, "member_object_id": wire_id})

    def add_jumper(wired_label, jumpered_label):
        nonlocal conn_counter
        w_obj = term_by_label.get(wired_label)
        j_obj = term_by_label.get(jumpered_label)
        if not w_obj or not j_obj:
            return
        cid = f"C{conn_counter}"
        conn_counter += 1
        new_connections.append({
            "connection_id": cid,
            "source_object_id": w_obj["system_object_id"],
            "target_object_id": j_obj["system_object_id"],
            "relationship_type": "JUMPER_SHORT",
        })

    # TOP GROUP
    if top_labels and top_cable_label:
        print(f"\n  Top group wiring ({top_cable_label}):")
        for i, lbl in enumerate(top_labels):
            color = WIRE_COLORS[i % len(WIRE_COLORS)]
            add_wire(lbl, top_cable_label, color)
            print(f"    {lbl} -[{color}]-> {top_cable_label}")

    # MAIN GROUP interleave
    closer_color_idx = 0
    farther_color_idx = 0
    print(f"\n  Main group wiring (interleave {closer_cable}/{farther_cable}):")
    for pair_idx, (wired_lbl, jumpered_lbl) in enumerate(wired_main):
        if pair_idx % 2 == 0:
            cable_lbl = closer_cable
            cross_cable_lbl = farther_cable
            color = WIRE_COLORS[closer_color_idx % len(WIRE_COLORS)]
            closer_color_idx += 1
        else:
            cable_lbl = farther_cable
            cross_cable_lbl = closer_cable
            color = WIRE_COLORS[farther_color_idx % len(WIRE_COLORS)]
            farther_color_idx += 1

        if cable_lbl:
            add_wire(wired_lbl, cable_lbl, color)
            print(f"    {wired_lbl} -[{color}]-> {cable_lbl}", end="")
        if jumpered_lbl:
            add_jumper(wired_lbl, jumpered_lbl)
            if cross_cable_lbl:
                add_wire(jumpered_lbl, cross_cable_lbl, color)
            print(f"  |  JUMPER: {wired_lbl} -> {jumpered_lbl}  |  {jumpered_lbl} -[{color}]-> {cross_cable_lbl}")
        else:
            print()

    return {
        "objects": new_objects,
        "connections": new_connections,
        "partition_memberships": new_partitions,
    }


if __name__ == "__main__":
    from cv_preprocess import extract_geometry, compute_cable_routing_map

    image_path = "test-data/image1-hires.png"
    geometry = extract_geometry(image_path)

    with open("output/image1-hires-out-20260315-180215-stage1-discovery.json") as f:
        disc = json.load(f)
    cable_list = disc.get("cables", [])
    cable_routing_map = compute_cable_routing_map(image_path, geometry, cable_list)

    with open("output/image1-hires-out-20260315-180215-stage2-raw.json") as f:
        parsed = json.load(f)

    print(f"Before: {len(parsed['objects'])} objects, {len(parsed['connections'])} connections")
    wires_before = sum(1 for o in parsed["objects"] if o.get("object_type") == "WIRE")
    print(f"  WIRE objects: {wires_before}\n")

    result = build_deterministic_connections(parsed, geometry, cable_routing_map, image_path)

    print(f"\n=== RESULT ===")
    print(f"Objects: {len(result['objects'])}, Connections: {len(result['connections'])}")
    wires = [o for o in result["objects"] if o.get("object_type") == "WIRE"]
    print(f"WIRE objects: {len(wires)}")

    obj_map = {o["system_object_id"]: o for o in result["objects"]}
    print("\nWire connections:")
    for c in result["connections"]:
        rt = c.get("relationship_type", "")
        if rt == "WIRE_TO_CABLE":
            wire = obj_map.get(c["source_object_id"], {}).get("raw_text", "?")
            cable = obj_map.get(c["target_object_id"], {}).get("raw_text", "?")
            term = "?"
            for c2 in result["connections"]:
                if c2.get("relationship_type") == "DIRECT_WIRE" and c2["target_object_id"] == c["source_object_id"]:
                    term = obj_map.get(c2["source_object_id"], {}).get("raw_text", "?")
            print(f"  {term} -[{wire}]-> {cable}")
        elif "JUMPER" in rt:
            s = obj_map.get(c["source_object_id"], {}).get("raw_text", "?")
            t = obj_map.get(c["target_object_id"], {}).get("raw_text", "?")
            print(f"  JUMPER: {s} -> {t}")
