"""
Stage 1 Service — OpenCV Geometry Extraction

Extracts deterministic wire geometry, dashed partition regions, slider terminals,
terminal rectangles, cable routing maps, and terminal wire analysis from
electrical schematic images using OpenCV.

All pixel thresholds are calibrated for REF_WIDTH=1536 and scale dynamically.
"""

import cv2
import numpy as np
import json
import sys
from pathlib import Path

REF_WIDTH = 1536


# ────────────────────────────────────────────────────────────────────────────
#  IMAGE LOADING
# ────────────────────────────────────────────────────────────────────────────

def load_and_preprocess(image_path: str):
    """Load image, convert to grayscale, produce binary mask."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return img, gray, binary


def load_binary_image(image_path: str):
    """Load image and return (gray, binary) tuple."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return gray, binary


# ────────────────────────────────────────────────────────────────────────────
#  WIRE DETECTION
# ────────────────────────────────────────────────────────────────────────────

def extract_wire_mask(binary, kernel_len=60, dilate_size=3):
    """Extract wire-like features using morphological opening."""
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
    h_wires = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))
    v_wires = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
    combined = cv2.bitwise_or(h_wires, v_wires)
    dilate_k = cv2.getStructuringElement(cv2.MORPH_RECT, (dilate_size, dilate_size))
    combined = cv2.dilate(combined, dilate_k, iterations=1)
    return combined


def detect_wires(wire_img, min_length=60, max_gap=20,
                 merge_gap=15, group_tol=8, min_seg_len=30):
    """Detect wire segments from morphologically-cleaned image."""
    results = []
    lines = cv2.HoughLinesP(
        wire_img, rho=1, theta=np.pi / 180,
        threshold=30, minLineLength=min_length, maxLineGap=max_gap
    )
    if lines is None:
        return results
    for seg in lines:
        x1, y1, x2, y2 = seg[0]
        length = np.hypot(x2 - x1, y2 - y1)
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180
        orient = _classify_orientation(angle)
        if orient == "diagonal":
            continue
        results.append({
            "x1": int(x1), "y1": int(y1),
            "x2": int(x2), "y2": int(y2),
            "length": round(float(length), 1),
            "angle": round(float(angle), 1),
            "orientation": orient,
        })
    results = _merge_collinear(results, gap=merge_gap, group_tol=group_tol, min_seg_len=min_seg_len)
    return results


def _classify_orientation(angle_deg):
    a = angle_deg % 180
    if a < 10 or a > 170:
        return "horizontal"
    if 80 < a < 100:
        return "vertical"
    return "diagonal"


def _merge_collinear(segments, gap=15, angle_tol=5, group_tol=8, min_seg_len=30):
    """Merge nearly-collinear overlapping segments into longer wires."""
    if not segments:
        return segments
    h_segs = [s for s in segments if s["orientation"] == "horizontal"]
    v_segs = [s for s in segments if s["orientation"] == "vertical"]
    merged = []
    merged.extend(_merge_group(h_segs, axis="horizontal", gap=gap, group_tol=group_tol, min_seg_len=min_seg_len))
    merged.extend(_merge_group(v_segs, axis="vertical", gap=gap, group_tol=group_tol, min_seg_len=min_seg_len))
    return merged


def _merge_group(segs, axis, gap, group_tol=8, min_seg_len=30):
    """Merge segments along one axis."""
    if not segs:
        return segs
    if axis == "horizontal":
        segs.sort(key=lambda s: (min(s["y1"], s["y2"]), min(s["x1"], s["x2"])))
        groups = []
        for s in segs:
            y = (s["y1"] + s["y2"]) / 2
            placed = False
            for g in groups:
                if abs(g["y"] - y) < group_tol:
                    g["segs"].append(s)
                    placed = True
                    break
            if not placed:
                groups.append({"y": y, "segs": [s]})

        merged = []
        for g in groups:
            intervals = []
            for s in g["segs"]:
                x_min = min(s["x1"], s["x2"])
                x_max = max(s["x1"], s["x2"])
                intervals.append((x_min, x_max))
            intervals.sort()
            combined = [intervals[0]]
            for start, end in intervals[1:]:
                if start <= combined[-1][1] + gap:
                    combined[-1] = (combined[-1][0], max(combined[-1][1], end))
                else:
                    combined.append((start, end))
            for x_min, x_max in combined:
                y_avg = int(round(g["y"]))
                length = x_max - x_min
                if length >= min_seg_len:
                    merged.append({
                        "x1": int(x_min), "y1": y_avg,
                        "x2": int(x_max), "y2": y_avg,
                        "length": round(float(length), 1),
                        "angle": 0.0,
                        "orientation": "horizontal",
                    })
        return merged
    else:
        segs.sort(key=lambda s: (min(s["x1"], s["x2"]), min(s["y1"], s["y2"])))
        groups = []
        for s in segs:
            x = (s["x1"] + s["x2"]) / 2
            placed = False
            for g in groups:
                if abs(g["x"] - x) < group_tol:
                    g["segs"].append(s)
                    placed = True
                    break
            if not placed:
                groups.append({"x": x, "segs": [s]})

        merged = []
        for g in groups:
            intervals = []
            for s in g["segs"]:
                y_min = min(s["y1"], s["y2"])
                y_max = max(s["y1"], s["y2"])
                intervals.append((y_min, y_max))
            intervals.sort()
            combined = [intervals[0]]
            for start, end in intervals[1:]:
                if start <= combined[-1][1] + gap:
                    combined[-1] = (combined[-1][0], max(combined[-1][1], end))
                else:
                    combined.append((start, end))
            for y_min, y_max in combined:
                x_avg = int(round(g["x"]))
                length = y_max - y_min
                if length >= min_seg_len:
                    merged.append({
                        "x1": x_avg, "y1": int(y_min),
                        "x2": x_avg, "y2": int(y_max),
                        "length": round(float(length), 1),
                        "angle": 90.0,
                        "orientation": "vertical",
                    })
        return merged


# ────────────────────────────────────────────────────────────────────────────
#  WIRE CHAIN CONNECTIVITY
# ────────────────────────────────────────────────────────────────────────────

def build_wire_chains(wires, join_radius=15):
    """Join wire segments whose endpoints are close or form T-junctions."""
    if not wires:
        return []
    n = len(wires)
    adj = {i: [] for i in range(n)}

    endpoints = []
    for i, w in enumerate(wires):
        endpoints.append((i, w["x1"], w["y1"]))
        endpoints.append((i, w["x2"], w["y2"]))
    for a in range(len(endpoints)):
        for b in range(a + 1, len(endpoints)):
            if endpoints[a][0] == endpoints[b][0]:
                continue
            dist = np.hypot(endpoints[a][1] - endpoints[b][1],
                            endpoints[a][2] - endpoints[b][2])
            if dist < join_radius:
                adj[endpoints[a][0]].append(endpoints[b][0])
                adj[endpoints[b][0]].append(endpoints[a][0])

    for i, wi in enumerate(wires):
        for ep_x, ep_y in [(wi["x1"], wi["y1"]), (wi["x2"], wi["y2"])]:
            for j, wj in enumerate(wires):
                if i == j or j in adj[i]:
                    continue
                if _point_near_segment(ep_x, ep_y, wj, join_radius):
                    adj[i].append(j)
                    adj[j].append(i)

    visited = set()
    chains = []
    for i in range(n):
        if i in visited:
            continue
        chain = []
        queue = [i]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            chain.append(node)
            for nb in adj[node]:
                if nb not in visited:
                    queue.append(nb)
        chains.append(chain)
    return chains


def _point_near_segment(px, py, wire, radius):
    """Check if point (px,py) is within radius of the wire segment body."""
    x1, y1, x2, y2 = wire["x1"], wire["y1"], wire["x2"], wire["y2"]
    if wire["orientation"] == "horizontal":
        xmin, xmax = min(x1, x2), max(x1, x2)
        if xmin - radius <= px <= xmax + radius and abs(py - y1) < radius:
            return True
    elif wire["orientation"] == "vertical":
        ymin, ymax = min(y1, y2), max(y1, y2)
        if ymin - radius <= py <= ymax + radius and abs(px - x1) < radius:
            return True
    return False


# ────────────────────────────────────────────────────────────────────────────
#  DASHED PARTITION DETECTION
# ────────────────────────────────────────────────────────────────────────────

def detect_dashed_regions(binary, scale=1.0):
    """Detect dashed-line partition boundary regions."""
    klen = max(int(30 * scale), 3)
    min_size = int(80 * scale)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (klen, 1))
    h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, klen))
    v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
    combined = cv2.bitwise_or(h_lines, v_lines)
    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > min_size or h > min_size:
            regions.append({"x": int(x), "y": int(y), "width": int(w), "height": int(h)})
    return regions


# ────────────────────────────────────────────────────────────────────────────
#  SLIDER DETECTION
# ────────────────────────────────────────────────────────────────────────────

def detect_slider_rects(binary, scale=1.0):
    """Detect terminal rectangles containing a slider (horizontal line with dots)."""
    min_w = int(30 * scale)
    max_w = int(120 * scale)
    min_h = int(12 * scale)
    max_h = int(60 * scale)
    min_aspect = 1.3
    max_aspect = 5.0
    coverage_threshold = 0.85
    min_band_rows = max(int(2 * scale), 2)

    contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    slider_rects = []
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) < 4:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        if not (min_w <= w <= max_w and min_h <= h <= max_h):
            continue
        aspect = w / h if h > 0 else 0
        if not (min_aspect <= aspect <= max_aspect):
            continue

        border = max(int(2 * scale), 2)
        interior = binary[y + border: y + h - border, x + border + 1: x + w - border - 1]
        if interior.size == 0:
            continue
        ih, iw = interior.shape

        band_count = 0
        for row_idx in range(ih):
            row = interior[row_idx, :]
            max_run = 0
            current_run = 0
            for px in row:
                if px > 0:
                    current_run += 1
                    if current_run > max_run:
                        max_run = current_run
                else:
                    current_run = 0
            if iw > 0 and max_run / iw >= coverage_threshold:
                band_count += 1
            else:
                band_count = 0
            if band_count >= min_band_rows:
                slider_rects.append({
                    "x": int(x), "y": int(y),
                    "width": int(w), "height": int(h),
                    "has_slider": True,
                })
                break

    return slider_rects


# ────────────────────────────────────────────────────────────────────────────
#  TERMINAL RECTANGLE DETECTION
# ────────────────────────────────────────────────────────────────────────────

def detect_terminal_rects(binary, scale=1.0):
    """Detect terminal-block rectangles. Returns list sorted by centre-Y."""
    min_w = int(30 * scale)
    max_w = int(120 * scale)
    min_h = int(12 * scale)
    max_h = int(60 * scale)

    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    rects = []
    img_w = binary.shape[1]
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) < 4:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if not (min_w <= bw <= max_w and min_h <= bh <= max_h):
            continue
        aspect = bw / bh if bh > 0 else 0
        if not (1.3 <= aspect <= 5.0):
            continue
        if x < img_w * 0.1:
            continue
        rects.append({"x": int(x), "y": int(y), "w": int(bw), "h": int(bh),
                       "cy": int(y + bh // 2)})

    rects.sort(key=lambda r: r["cy"])
    deduped = []
    for r in rects:
        if not deduped or abs(r["cy"] - deduped[-1]["cy"]) > 5:
            deduped.append(r)
        else:
            if r["w"] * r["h"] > deduped[-1]["w"] * deduped[-1]["h"]:
                deduped[-1] = r
    return deduped


# ────────────────────────────────────────────────────────────────────────────
#  INTERSECTION ANALYSIS — BEND vs STRAIGHT at wire/bus crossings
# ────────────────────────────────────────────────────────────────────────────

def analyze_intersection_pixels(binary, ix, iy, scale=1.0):
    """Pixel-level BEND/STRAIGHT/DOT verdict at a wire-bus-line intersection."""
    h, w = binary.shape

    region_r = max(int(30 * scale), 20)
    band_half = max(int(3 * scale), 2)
    check_start = max(int(8 * scale), 5)
    check_end = max(int(25 * scale), 18)
    dot_r = max(int(6 * scale), 4)
    h_kernel_len = max(int(12 * scale), 8)

    if (ix < check_end + 2 or ix >= w - check_end - 2 or
            iy < region_r or iy >= h - region_r):
        return {
            "verdict": "UNCLEAR",
            "evidence": "Intersection too close to image edge for reliable analysis.",
            "metrics": {"left_density": 0, "right_density": 0,
                        "continuity_ratio": 0, "dot_score": 0},
        }

    y1c, y2c = max(0, iy - region_r), min(h, iy + region_r)
    x1c, x2c = max(0, ix - region_r), min(w, ix + region_r)
    crop = binary[y1c:y2c, x1c:x2c]
    cx, cy = ix - x1c, iy - y1c

    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_len, 1))
    h_open = cv2.morphologyEx(crop, cv2.MORPH_OPEN, h_kernel)

    band_top = max(0, cy - band_half)
    band_bot = min(h_open.shape[0], cy + band_half + 1)

    left_col_s = max(0, cx - check_end)
    left_col_e = max(0, cx - check_start)
    left_zone = h_open[band_top:band_bot, left_col_s:left_col_e]
    left_density = float(np.mean(left_zone > 0)) if left_zone.size > 0 else 0.0

    right_col_s = min(h_open.shape[1], cx + check_start)
    right_col_e = min(h_open.shape[1], cx + check_end)
    right_zone = h_open[band_top:band_bot, right_col_s:right_col_e]
    right_density = float(np.mean(right_zone > 0)) if right_zone.size > 0 else 0.0

    dot_zone = crop[max(0, cy - dot_r):min(crop.shape[0], cy + dot_r + 1),
                    max(0, cx - dot_r):min(crop.shape[1], cx + dot_r + 1)]
    dot_score = float(np.mean(dot_zone > 0)) if dot_zone.size > 0 else 0.0

    wire_threshold = 0.12
    left_present = left_density > wire_threshold
    right_present = right_density > wire_threshold

    if dot_score > 0.60:
        verdict = "DOT"
        evidence = (
            f"Junction dot/node detected (dot_score={dot_score:.2f}). "
            f"Wire CONNECTS to this bus line via explicit junction dot."
        )
    elif left_present and right_present:
        continuity = (min(left_density, right_density) /
                      max(left_density, right_density))
        verdict = "STRAIGHT"
        evidence = (
            f"Horizontal wire continues on BOTH sides of the bus line "
            f"(left={left_density:.2f}, right={right_density:.2f}, "
            f"continuity={continuity:.2f}). "
            f"Wire CROSSES OVER — NOT connected to this bus line."
        )
    elif left_present or right_present:
        present_side = "left" if left_present else "right"
        absent_side = "right" if left_present else "left"
        verdict = "BEND"
        evidence = (
            f"Horizontal wire present on {present_side} side "
            f"(density={max(left_density, right_density):.2f}) "
            f"but ABSENT on {absent_side} side "
            f"(density={min(left_density, right_density):.2f}). "
            f"Wire BENDS at this bus line — CONNECTED."
        )
    else:
        verdict = "UNCLEAR"
        evidence = (
            f"No significant horizontal wire pixels on either side "
            f"(left={left_density:.2f}, right={right_density:.2f}). "
            f"Wire may not pass through this y-coordinate at this bus line."
        )

    cont_ratio = (min(left_density, right_density) /
                  max(left_density, right_density)
                  if max(left_density, right_density) > 0 else 0.0)

    return {
        "verdict": verdict,
        "evidence": evidence,
        "metrics": {
            "left_density": round(left_density, 3),
            "right_density": round(right_density, 3),
            "continuity_ratio": round(cont_ratio, 3),
            "dot_score": round(dot_score, 3),
        },
    }


def batch_analyze_intersections(binary, wire_y, bus_lines, scale=1.0):
    """Analyze a horizontal wire against all bus lines."""
    results = []
    for bi, bl in enumerate(bus_lines):
        label = chr(ord("A") + bi)
        bx = bl["x1"]
        analysis = analyze_intersection_pixels(binary, bx, wire_y, scale=scale)
        results.append({
            "bus_label": label,
            "bus_x": bx,
            **analysis,
        })
    return results


# ────────────────────────────────────────────────────────────────────────────
#  CABLE ROUTING MAP
# ────────────────────────────────────────────────────────────────────────────

def compute_cable_routing_map(image_path, geometry, discovery_cables):
    """Detect cable circles and compute horizontal-wire to cable routing by y-proximity."""
    import re as _re

    if not discovery_cables:
        return {}

    seen_labels = {}
    for c in discovery_cables:
        if not isinstance(c, dict):
            continue
        norm = _re.sub(r'\s+', '', c.get("label", ""))
        if not norm:
            continue
        pos = c.get("position", "")
        if norm not in seen_labels or "center" in pos:
            seen_labels[norm] = c
    unique_cables = list(seen_labels.values())
    n_cables = len(unique_cables)
    if n_cables == 0:
        return {}

    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return {}
    h, w = gray.shape

    dashed = geometry.get("dashed_regions", [])
    cable_zones = [d for d in dashed if d["height"] > 100 and d["width"] > 50]
    cable_zones.sort(key=lambda d: d["height"] * d["width"], reverse=True)
    if not cable_zones:
        return {}

    zone = cable_zones[0]
    zx, zy, zw, zh = zone["x"], zone["y"], zone["width"], zone["height"]

    pad = 10
    y1 = max(0, zy - pad)
    y2 = min(h, zy + zh + pad)
    x1 = max(0, zx - pad)
    x2 = min(w, zx + zw + pad)
    sub_img = gray[y1:y2, x1:x2]
    sub_blur = cv2.GaussianBlur(sub_img, (5, 5), 0)

    circles = None
    for param2 in [40, 30, 20, 15]:
        circles = cv2.HoughCircles(
            sub_blur, cv2.HOUGH_GRADIENT, dp=1.2,
            minDist=30, param1=80, param2=param2,
            minRadius=8, maxRadius=45,
        )
        if circles is not None and len(circles[0]) >= n_cables:
            break

    if circles is None:
        return {}

    all_circles = []
    for c in circles[0]:
        cx, cy, r = int(c[0]) + x1, int(c[1]) + y1, int(c[2])
        all_circles.append({"x": cx, "y": cy, "r": r})

    all_circles.sort(key=lambda c: c["r"], reverse=True)
    cable_circles = sorted(all_circles[:n_cables], key=lambda c: c["y"])

    if len(cable_circles) < n_cables:
        return {}

    pos_order = {"top": 0, "middle": 1, "bottom": 2}
    sorted_cables = sorted(
        unique_cables,
        key=lambda c: pos_order.get(c.get("position", "middle").split("-")[0], 1),
    )

    cable_y_map = {}
    labeled_circles = []
    for i, cable in enumerate(sorted_cables):
        label = _re.sub(r'\s+', '', cable["label"])
        cable_y_map[label] = cable_circles[i]["y"]
        labeled_circles.append({**cable_circles[i], "label": label})

    circle_ys = [c["y"] for c in cable_circles]
    boundaries = []
    for i in range(len(circle_ys)):
        y_lo = 0 if i == 0 else (circle_ys[i - 1] + circle_ys[i]) // 2
        y_hi = h if i == len(circle_ys) - 1 else (circle_ys[i] + circle_ys[i + 1]) // 2
        label = _re.sub(r'\s+', '', sorted_cables[i]["label"])
        boundaries.append({"y_lo": y_lo, "y_hi": y_hi, "label": label})

    h_wires = sorted(
        [ww for ww in geometry.get("wires", []) if ww["orientation"] == "horizontal"],
        key=lambda ww: ww["y1"],
    )
    if not h_wires:
        return {}

    routing = []
    for hw in h_wires:
        hw_y = hw["y1"]
        for bnd in boundaries:
            if bnd["y_lo"] <= hw_y < bnd["y_hi"]:
                cable_y = cable_y_map[bnd["label"]]
                dist = abs(hw_y - cable_y)
                confidence = "HIGH" if dist < 50 else "MEDIUM" if dist < 80 else "LOW"
                routing.append({
                    "hw_y": hw_y,
                    "cable_label": bnd["label"],
                    "cable_circle_y": cable_y,
                    "distance": dist,
                    "confidence": confidence,
                })
                break

    return {
        "routing": routing,
        "cable_circles": labeled_circles,
        "boundaries": boundaries,
    }


# ────────────────────────────────────────────────────────────────────────────
#  TERMINAL WIRE ANALYSIS — Right-side wires and jumper pairs
# ────────────────────────────────────────────────────────────────────────────

def analyze_terminal_wires(image_path, geometry, discovery_terminals):
    """Detect which terminals have right-side cable wires and identify jumper pairs."""
    if not discovery_terminals:
        return {}

    img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        return {}
    _, binary = cv2.threshold(img_gray, 0, 255,
                              cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = binary.shape
    scale = max(w / REF_WIDTH, 1.0)

    term_rects = detect_terminal_rects(binary, scale)
    if len(term_rects) != len(discovery_terminals):
        return {}

    dashed = geometry.get("dashed_regions", [])
    cable_zones = sorted(
        [d for d in dashed if d["height"] > 100 and d["width"] > 50],
        key=lambda d: d["height"] * d["width"], reverse=True,
    )
    cable_zone_right = 380
    if cable_zones:
        cz = cable_zones[0]
        cable_zone_right = cz["x"] + cz["width"]

    results = []
    for i, r in enumerate(term_rects):
        label = discovery_terminals[i].get("label", f"T{i}")
        cy = r["cy"]

        wire_len = 0
        for x in range(cable_zone_right, min(w, cable_zone_right + 30)):
            window = binary[max(0, cy - 1):cy + 2, x]
            if np.any(window > 0):
                wire_len += 1
            else:
                ahead = binary[max(0, cy - 1):cy + 2,
                               x:min(w, x + 4)]
                if not np.any(ahead > 0):
                    break

        has_right_wire = wire_len > 5
        results.append({
            "label": label,
            "cy": cy,
            "has_right_wire": has_right_wire,
            "jumper_partner": None,
            "wire_side": "RIGHT" if has_right_wire else "LEFT_ONLY",
        })

    jumper_pairs = []
    for i, info in enumerate(results):
        if info["has_right_wire"]:
            continue
        partner_idx = None
        if i > 0 and results[i - 1]["has_right_wire"]:
            partner_idx = i - 1
        elif i < len(results) - 1 and results[i + 1]["has_right_wire"]:
            partner_idx = i + 1
        if partner_idx is not None:
            info["jumper_partner"] = results[partner_idx]["label"]
            jumper_pairs.append((results[partner_idx]["label"], info["label"]))

    return {
        "terminal_info": results,
        "jumper_pairs": jumper_pairs,
    }


# ────────────────────────────────────────────────────────────────────────────
#  MAIN EXTRACTION PIPELINE
# ────────────────────────────────────────────────────────────────────────────

def extract_geometry(image_path: str, output_path: str = None) -> dict:
    """Full geometry extraction pipeline. Returns structured dict.

    If output_path is provided, saves the geometry JSON to that path.
    """
    img, gray, binary = load_and_preprocess(image_path)
    h, w = gray.shape[:2]
    scale = max(w / REF_WIDTH, 1.0)

    dashed = detect_dashed_regions(binary, scale=scale)
    slider_rects = detect_slider_rects(binary, scale=scale)

    wire_img = extract_wire_mask(binary,
                                  kernel_len=int(60 * scale),
                                  dilate_size=max(int(3 * scale), 1))
    wires = detect_wires(wire_img,
                          min_length=int(60 * scale),
                          max_gap=int(20 * scale),
                          merge_gap=int(15 * scale),
                          group_tol=int(8 * scale),
                          min_seg_len=int(30 * scale))

    chains = build_wire_chains(wires, join_radius=int(15 * scale))

    multi_chain_idxs = set()
    for ch in chains:
        if len(ch) > 1:
            multi_chain_idxs.update(ch)
    if multi_chain_idxs:
        idx_map = {}
        new_wires = []
        for old_i in sorted(multi_chain_idxs):
            idx_map[old_i] = len(new_wires)
            new_wires.append(wires[old_i])
        wires = new_wires
        chains = build_wire_chains(wires, join_radius=int(15 * scale))

    result = {
        "image_size": {"width": w, "height": h},
        "scale": round(scale, 3),
        "summary": {
            "wires": len(wires),
            "wire_chains": len(chains),
            "dashed_regions": len(dashed),
            "slider_terminals": len(slider_rects),
        },
        "wires": wires,
        "wire_chains": [{"chain_id": i, "wire_indices": c} for i, c in enumerate(chains)],
        "dashed_regions": dashed,
        "slider_rects": slider_rects,
    }

    if output_path:
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

    return result


def format_wire_map(geometry: dict) -> str:
    """Format geometry into a concise wire map for LLM prompt injection."""
    s = geometry["summary"]

    # Safety cap: summarize if OpenCV is too noisy
    if s["wires"] > 200:
        return (
            f"Image: {geometry['image_size']['width']}\u00d7{geometry['image_size']['height']}px  "
            f"(scale={geometry.get('scale', 1.0):.1f}x)\n"
            f"OpenCV found: {s['wires']} wire segments ({s['wire_chains']} chains) \u2014 "
            f"TOO NOISY for detailed wire map."
        )

    out = []
    out.append(f"Image: {geometry['image_size']['width']}\u00d7{geometry['image_size']['height']}px")
    out.append(f"OpenCV found: {s['wires']} wire segments ({s['wire_chains']} chains)")
    out.append("")

    h_wires = [w for w in geometry["wires"] if w["orientation"] == "horizontal"]
    v_wires = [w for w in geometry["wires"] if w["orientation"] == "vertical"]
    h_wires.sort(key=lambda w: w["y1"])
    v_wires.sort(key=lambda w: w["x1"])

    if h_wires:
        out.append("HORIZONTAL WIRES (top \u2192 bottom):")
        for i, w in enumerate(h_wires):
            out.append(f"  HW{i}: ({w['x1']},{w['y1']})\u2192({w['x2']},{w['y2']})  len={w['length']}px")
        out.append("")

    if v_wires:
        out.append("VERTICAL WIRES (left \u2192 right):")
        for i, w in enumerate(v_wires):
            out.append(f"  VW{i}: ({w['x1']},{w['y1']})\u2192({w['x2']},{w['y2']})  len={w['length']}px")
        out.append("")

    if v_wires:
        max_vlen = max(w["length"] for w in v_wires)
        bus_lines = sorted(
            [w for w in v_wires if w["length"] >= max_vlen * 0.85],
            key=lambda w: w["x1"],
        )
        if len(bus_lines) >= 2:
            out.append("\u26a0\ufe0f  VERTICAL BUS LINES DETECTED BY OpenCV (ground-truth positions):")
            out.append("    These are the full-span vertical lines that route wires to cables.")
            out.append("    Each bus line feeds a DIFFERENT cable. When tracing a wire,")
            out.append("    check what happens at EACH bus line x-position:")
            out.append("      \u2022 BEND/CURVE at this x \u2192 wire CONNECTS to this bus line's cable")
            out.append("      \u2022 STRAIGHT pass-through at this x \u2192 wire CROSSES OVER (not connected)")
            for bi, bl in enumerate(bus_lines):
                label = chr(ord("A") + bi)
                out.append(
                    f"    BUS LINE {label}: x\u2248{bl['x1']}  "
                    f"(y={bl['y1']}\u2192{bl['y2']}, {int(bl['length'])}px)"
                )
            out.append(
                f"    Wires between x\u2248{bus_lines[0]['x1']} and x\u2248{bus_lines[-1]['x1']} "
                f"are individual wire runs \u2014 NOT bus lines."
            )
            out.append("")

    if geometry["wire_chains"]:
        out.append("WIRE CHAINS (connected segments forming paths):")
        for ch in geometry["wire_chains"]:
            wire_indices = ch["wire_indices"]
            if len(wire_indices) > 1:
                wire_descs = []
                for idx in wire_indices:
                    w = geometry["wires"][idx]
                    wire_descs.append(f"{w['orientation'][0].upper()}({w['x1']},{w['y1']})\u2192({w['x2']},{w['y2']})")
                out.append(f"  Chain{ch['chain_id']}: {' \u2192 '.join(wire_descs)}")
        out.append("")

    slider_rects = geometry.get("slider_rects", [])
    dashed_regions = geometry.get("dashed_regions", [])
    if slider_rects:
        out.append("SLIDER TERMINALS (OpenCV-detected):")
        for sr in slider_rects:
            sx, sy, sh = sr["x"], sr["y"], sr["height"]
            slider_cy = sy + sh / 2
            ordinal_hint = ""
            for dr in dashed_regions:
                if (dr["x"] <= sx <= dr["x"] + dr["width"]
                        and dr["y"] <= sy <= dr["y"] + dr["height"]
                        and dr["height"] > 10):
                    frac = (slider_cy - dr["y"]) / dr["height"]
                    pct = int(frac * 100)
                    ordinal_hint = (
                        f" \u2014 ~{pct}% from top of terminal block "
                        f"({dr['x']},{dr['y']}) {dr['width']}\u00d7{dr['height']}px"
                    )
                    break
            out.append(
                f"  rect ({sr['x']},{sr['y']}) {sr['width']}\u00d7{sr['height']}px \u2192 has_slider=TRUE{ordinal_hint}"
            )
        out.append("")

    return "\n".join(out)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "test-data/test-diagram.png"
    geometry = extract_geometry(path)
    print(json.dumps(geometry["summary"], indent=2))
    print()
    print(format_wire_map(geometry))
