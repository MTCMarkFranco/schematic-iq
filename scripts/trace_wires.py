"""Trace wire paths from terminals through the bus network to HW wires.
Uses the raw binary image since morphological wire extraction misses short stubs."""
import cv2
import numpy as np
import json, glob, sys
sys.path.insert(0, ".")
from cv_preprocess import load_and_preprocess

image_path = "test-data/image.png"
img, gray, binary = load_and_preprocess(image_path)
h, w = gray.shape

# Load latest geometry and discovery
geo_f = sorted(glob.glob("output/*stage0-geometry.json"))[-1]
disc_f = sorted(glob.glob("output/*stage1-discovery.json"))[-1]
with open(geo_f) as f: geo = json.load(f)
with open(disc_f) as f: disc = json.load(f)

# Terminal rects (sorted by y, from detect_all_terms.py results)
# Redetect them here
scale = max(w / 1536, 1.0)
min_rw, max_rw = int(30 * scale), int(120 * scale)
min_rh, max_rh = int(12 * scale), int(60 * scale)
contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
term_rects = []
for cnt in contours:
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
    if len(approx) < 4:
        continue
    x, y, bw, bh = cv2.boundingRect(cnt)
    if not (min_rw <= bw <= max_rw and min_rh <= bh <= max_rh):
        continue
    aspect = bw / bh if bh > 0 else 0
    if not (1.3 <= aspect <= 5.0):
        continue
    if x < w * 0.1:
        continue
    term_rects.append({"x": x, "y": y, "w": bw, "h": bh, "cy": y + bh // 2})
term_rects.sort(key=lambda r: r["cy"])
deduped = []
for r in term_rects:
    if not deduped or abs(r["cy"] - deduped[-1]["cy"]) > 5:
        deduped.append(r)
    else:
        if r["w"] * r["h"] > deduped[-1]["w"] * deduped[-1]["h"]:
            deduped[-1] = r

terms = disc.get("terminals", [])
h_wires = sorted([ww for ww in geo["wires"] if ww["orientation"] == "horizontal"], key=lambda ww: ww["y1"])
hw_ys = [ww["y1"] for ww in h_wires]

print(f"Image: {w}x{h}")
print(f"Terminal rects: {len(deduped)}, Discovery terminals: {len(terms)}")
print(f"HW y positions: {hw_ys}")

# 1. Check what column the terminal's wire exits from  
# Terminal rects left edge = x=320. Check binary pixels going left from x=319
print("\n=== Wire traces from each terminal ===")
for i, r in enumerate(deduped):
    cy = r["cy"]
    label = terms[i]["label"] if i < len(terms) else "?"
    
    # Scan left from terminal left edge to find wire
    found_x = None
    for x in range(r["x"] - 1, 0, -1):
        if binary[cy, x] > 0:
            found_x = x
            break
    
    if found_x is None:
        print(f"  {label:6s} cy={cy:4d}: no wire found going left")
        continue
    
    # Follow the wire left until it ends or turns
    wire_end_x = found_x
    for x in range(found_x, 0, -1):
        # Check a small vertical window (allow slight vertical drift)
        window = binary[max(0,cy-2):cy+3, x]
        if np.any(window > 0):
            wire_end_x = x
        else:
            break
    
    print(f"  {label:6s} cy={cy:4d}: wire exits at x={found_x}, extends left to x={wire_end_x}")

# 2. Look at the vertical bus structure
# Check column profiles at key x positions
print("\n=== Vertical profile at x=200 (bus area) ===")
x_check = 200
col = binary[:, x_check]
runs = []
in_run = False
start = 0
for y in range(h):
    if col[y] > 0:
        if not in_run:
            in_run = True
            start = y
    else:
        if in_run:
            in_run = False
            runs.append((start, y-1))
if in_run:
    runs.append((start, h-1))
print(f"  Foreground runs at x={x_check}: {len(runs)}")
for s, e in runs:
    print(f"    y={s:4d}..{e:4d} (len={e-s+1})")

# 3. Check what's at the junction of each terminal's cy and each HW y along the vertical bus
print("\n=== Junction analysis at vertical bus ===")
# Find vertical bus x positions - look for long vertical runs
v_wires = sorted([ww for ww in geo["wires"] if ww["orientation"] == "vertical"], key=lambda ww: ww["x1"])
print(f"Vertical wires: {len(v_wires)}")
for vw in v_wires[:10]:
    print(f"  x={vw['x1']:4d}  y={vw['y1']:4d}..{vw['y2']:4d}  len={vw['y2']-vw['y1']}")

# 4. For terminals 964 (index 4) and 963 (index 5), trace in detail
for idx in [4, 5]:
    if idx >= len(deduped):
        continue
    r = deduped[idx]
    cy = r["cy"]
    label = terms[idx]["label"] if idx < len(terms) else "?"
    print(f"\n=== Detailed trace for terminal {label} (cy={cy}) ===")
    
    # From terminal left edge, trace left on binary
    # Show pixel presence at each column
    x_start = r["x"] - 1
    print(f"  Terminal rect: x={r['x']}, y={r['y']}, w={r['w']}, h={r['h']}")
    print(f"  Tracing left from x={x_start}, y={cy}")
    
    # Check binary pixels at y=cy going left
    horizontal_trace = []
    for x in range(x_start, max(0, x_start - 200), -1):
        # Check a 5-pixel tall window centered on cy
        window = binary[max(0,cy-2):min(h,cy+3), x]
        if np.any(window > 0):
            # Find exact y of the foreground pixel(s)
            ys_on = [cy-2+dy for dy in range(len(window)) if window[dy] > 0]
            horizontal_trace.append((x, ys_on))
    
    if horizontal_trace:
        first_x = horizontal_trace[0][0]
        last_x = horizontal_trace[-1][0]
        print(f"  Horizontal wire: x={last_x}..{first_x} at y≈{cy}")
    
    # At the leftmost point of the horizontal trace, look for vertical continuation
    if horizontal_trace:
        bus_x = horizontal_trace[-1][0]
        bus_ys = horizontal_trace[-1][1]
        print(f"  Bus junction at x={bus_x}, y={bus_ys}")
        
        # Trace DOWN from (bus_x, cy) looking for connection to HW
        print(f"  Tracing DOWN from x={bus_x}, y={cy}:")
        for y_check in range(cy, min(h, cy + 200)):
            # Check a 5-pixel wide window centered on bus_x
            window = binary[y_check, max(0,bus_x-2):min(w,bus_x+3)]
            if np.any(window > 0):
                # Is this y near an HW?
                for hw_y in hw_ys:
                    if abs(y_check - hw_y) <= 2:
                        print(f"    → Reaches HW y={hw_y} at row {y_check}")
            else:
                print(f"    Gap at y={y_check}, vertical wire ends")
                break
        
        # Also trace UP
        print(f"  Tracing UP from x={bus_x}, y={cy}:")
        for y_check in range(cy, max(0, cy - 200), -1):
            window = binary[y_check, max(0,bus_x-2):min(w,bus_x+3)]
            if np.any(window > 0):
                for hw_y in hw_ys:
                    if abs(y_check - hw_y) <= 2:
                        print(f"    → Reaches HW y={hw_y} at row {y_check}")
            else:
                print(f"    Gap at y={y_check}, vertical wire ends")
                break
