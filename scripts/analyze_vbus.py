"""Analyze vertical bus lines from OpenCV geometry."""
import json

d = json.load(open("output/image-out-20260314-094017-stage0-geometry.json"))
vw = [w for w in d["wires"] if w["orientation"] == "vertical"]
vw.sort(key=lambda w: w["x1"])

print("VERTICAL WIRES (left→right):")
for w in vw:
    span = w["y2"] - w["y1"]
    print(f"  x={w['x1']}  y={w['y1']}→{w['y2']}  span={span}px  len={w['length']}")

# Group by approximate x position
groups = {}
for w in vw:
    x = w["x1"]
    placed = False
    for gx in groups:
        if abs(x - gx) < 5:
            groups[gx].append(w)
            placed = True
            break
    if not placed:
        groups[x] = [w]

print("\nGROUPED BY X POSITION:")
for gx in sorted(groups):
    wires = groups[gx]
    total_span = sum(w["y2"] - w["y1"] for w in wires)
    print(f"  x≈{gx}: {len(wires)} segment(s), total span={total_span}px")
    for w in wires:
        print(f"    y={w['y1']}→{w['y2']}  ({w['y2']-w['y1']}px)")

# Identify the two longest vertical lines (likely bus lines)
print("\nLONGEST VERTICAL WIRES (candidate bus lines):")
vw_sorted = sorted(vw, key=lambda w: w["length"], reverse=True)
for w in vw_sorted[:5]:
    print(f"  x={w['x1']}  y={w['y1']}→{w['y2']}  len={w['length']}px")
