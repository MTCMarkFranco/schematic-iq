"""Detect all terminal rectangles and map each to nearest horizontal wire."""
import cv2
import numpy as np
import json, glob, sys
sys.path.insert(0, ".")
from cv_preprocess import load_and_preprocess, compute_cable_routing_map

image_path = "test-data/image.png"
img, gray, binary = load_and_preprocess(image_path)
h, w = gray.shape

# Load latest geometry and discovery
geo_f = sorted(glob.glob("output/*stage0-geometry.json"))[-1]
disc_f = sorted(glob.glob("output/*stage1-discovery.json"))[-1]
with open(geo_f) as f: geo = json.load(f)
with open(disc_f) as f: disc = json.load(f)

# Find ALL terminal-like rectangles (similar to detect_slider_rects but without the slider check)
scale = max(w / 1536, 1.0)
min_w, max_w = int(30 * scale), int(120 * scale)
min_h, max_h = int(12 * scale), int(60 * scale)
min_aspect, max_aspect = 1.3, 5.0

contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

term_rects = []
for cnt in contours:
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
    if len(approx) < 4:
        continue
    x, y, bw, bh = cv2.boundingRect(cnt)
    if not (min_w <= bw <= max_w and min_h <= bh <= max_h):
        continue
    aspect = bw / bh if bh > 0 else 0
    if not (min_aspect <= aspect <= max_aspect):
        continue
    # Must be on the right side (terminal block area)
    if x < w * 0.1:  # terminals are at least 10% from left edge
        continue
    term_rects.append({"x": x, "y": y, "w": bw, "h": bh, "cy": y + bh // 2})

# Deduplicate very close rects (within 5px of each other)
term_rects.sort(key=lambda r: r["cy"])
deduped = []
for r in term_rects:
    if not deduped or abs(r["cy"] - deduped[-1]["cy"]) > 5:
        deduped.append(r)
    else:
        # Keep larger one
        if r["w"] * r["h"] > deduped[-1]["w"] * deduped[-1]["h"]:
            deduped[-1] = r

print(f"Found {len(deduped)} terminal rectangles (expected 18)")
for i, r in enumerate(deduped):
    print(f"  #{i:2d}: x={r['x']:4d} y={r['y']:4d} w={r['w']:3d} h={r['h']:3d} center_y={r['cy']:4d}")

# Horizontal wires
h_wires = sorted([ww for ww in geo["wires"] if ww["orientation"] == "horizontal"], key=lambda ww: ww["y1"])
print(f"\nHorizontal wires: {len(h_wires)}")
for w_ in h_wires:
    print(f"  HW y={w_['y1']}")

# Map each rect to nearest HW
print("\n=== Terminal Rect → Nearest HW ===")
for i, r in enumerate(deduped):
    best_hw = min(h_wires, key=lambda ww: abs(ww["y1"] - r["cy"]))
    dist = abs(best_hw["y1"] - r["cy"])
    print(f"  #{i:2d} cy={r['cy']:4d} → HW y={best_hw['y1']:4d} (dist={dist:3d})")

# Discovery terminals (ordered top to bottom)
terms = disc.get("terminals", [])
print(f"\nDiscovery terminals: {len(terms)}")
for i, t in enumerate(terms):
    print(f"  #{i:2d}: {t.get('label','?')}")

# If counts match, pair them
if len(deduped) == len(terms):
    print("\n=== Terminal → HW → Cable ===")
    routing_map = compute_cable_routing_map(image_path, geo, disc.get("cables", []))
    boundaries = routing_map.get("boundaries", [])
    for i, (r, t) in enumerate(zip(deduped, terms)):
        best_hw = min(h_wires, key=lambda ww: abs(ww["y1"] - r["cy"]))
        hw_y = best_hw["y1"]
        cable = "?"
        for bnd in boundaries:
            if bnd["y_lo"] <= hw_y < bnd["y_hi"]:
                cable = bnd["label"]
                break
        label = t.get("label", "?")
        print(f"  {label:6s}  rect_cy={r['cy']:4d}  HW y={hw_y:4d}  → {cable}")
else:
    print(f"\nMISMATCH: {len(deduped)} rects vs {len(terms)} terminals")
