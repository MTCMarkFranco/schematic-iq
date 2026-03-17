"""Check which terminals have wires going RIGHT (past the terminal rect).
Terminals with right-side wires may connect directly to cable labels visible 
at the right side of the schematic."""
import cv2
import numpy as np
import json, glob, sys
sys.path.insert(0, ".")
from cv_preprocess import load_and_preprocess

image_path = "test-data/image.png"
img, gray, binary = load_and_preprocess(image_path)
h, w = gray.shape

disc_f = sorted(glob.glob("output/*stage1-discovery.json"))[-1]
with open(disc_f) as f: disc = json.load(f)

# Terminal rects (from previous detection)
scale = max(w / 1536, 1.0)
min_rw, max_rw = int(30 * scale), int(120 * scale)
min_rh, max_rh = int(12 * scale), int(60 * scale)
contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
term_rects = []
for cnt in contours:
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
    if len(approx) < 4: continue
    x, y, bw, bh = cv2.boundingRect(cnt)
    if not (min_rw <= bw <= max_rw and min_rh <= bh <= max_rh): continue
    aspect = bw / bh if bh > 0 else 0
    if not (1.3 <= aspect <= 5.0): continue
    if x < w * 0.1: continue
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
print(f"Terminals: {len(deduped)} rects, {len(terms)} discovery\n")

# Check right-side wire for each terminal
# A wire going RIGHT extends past the cable zone right border (~x=380)
cable_zone_right = 380

print(f"{'Term':>6s}  {'cy':>4s}  {'RectR':>5s}  {'RightWire':>10s}  {'RightLen':>8s}  {'FarRight':>8s}")
print("-" * 60)

for i, r in enumerate(deduped):
    label = terms[i]["label"] if i < len(terms) else "?"
    cy = r["cy"]
    rect_right = r["x"] + r["w"]
    
    # Check for right-side wire: scan from rect right edge to image right
    # Use a 3-pixel tall window centered on cy
    has_right_wire = False
    right_wire_len = 0
    right_wire_end = rect_right
    
    # Count consecutive foreground columns starting from cable_zone_right
    for x in range(cable_zone_right, min(w, 600)):
        window = binary[max(0,cy-1):cy+2, x]
        if np.any(window > 0):
            right_wire_len += 1
            right_wire_end = x
        else:
            if right_wire_len > 3:
                break  # Found the wire end
            # Allow small gaps (up to 3 pixels)
            ahead = binary[max(0,cy-1):cy+2, x:min(w, x+4)]
            if not np.any(ahead > 0):
                break
    
    has_right_wire = right_wire_len > 5
    
    # Also check far-right (x=420+) for any content at this y level
    far_right_content = np.count_nonzero(binary[max(0,cy-5):cy+6, 420:min(w, 550)])
    
    rw_str = f"YES ({right_wire_len}px)" if has_right_wire else "NO"
    print(f"{label:>6s}  {cy:4d}  {rect_right:5d}  {rw_str:>10s}  {right_wire_end:>8d}  {far_right_content:>8d}")

# Visualize the right-side area for terminals 964, 963, 962, 961
print("\n\n=== Right-side detail for key terminals ===")
for idx in [4, 5, 6, 7, 8, 9, 10, 11]:  # 964, 963, 962, 961, 960, 959, 958, 957
    if idx >= len(deduped): break
    r = deduped[idx]
    cy = r["cy"]
    label = terms[idx]["label"] if idx < len(terms) else "?"
    
    print(f"\n--- Terminal {label} (cy={cy}) right side (x=375..500) ---")
    for dy in range(-1, 2):
        y = cy + dy
        row = f"  y={y:4d}: "
        for x in range(375, min(w, 501)):
            if binary[y, x] > 0:
                row += "#"
            else:
                row += "."
        print(row)
