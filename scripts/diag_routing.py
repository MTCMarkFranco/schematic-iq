"""Diagnostic: test connected-component routing approach for wire-to-cable mapping."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from cv_preprocess import extract_geometry, load_binary_image

IMAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test-data", "image.png")

geom = extract_geometry(IMAGE)
_, binary = load_binary_image(IMAGE)
h, w = binary.shape
scale = geom.get("scale", 1.0)

h_wires = sorted([w2 for w2 in geom["wires"] if w2["orientation"] == "horizontal"], key=lambda w2: w2["y1"])
v_wires = sorted([w2 for w2 in geom["wires"] if w2["orientation"] == "vertical"], key=lambda w2: w2["x1"])

# Identify individual vertical runs (shorter than bus lines but significant)
max_vlen = max(vw["length"] for vw in v_wires)
bus_threshold = max_vlen * 0.85
individual_runs = sorted(
    [vw for vw in v_wires if 80 < vw["length"] < bus_threshold],
    key=lambda vw: vw["x1"]
)
ind_run_x = sorted(set(vw["x1"] for vw in individual_runs))
print(f"Individual vertical run x-positions: {ind_run_x}")

# ── Approach: Connected components with horizontal dilation ──
print("\n═══ Connected components with horizontal dilation ═══\n")

for dilation_w in [7, 9, 11, 13, 15]:
    # Horizontal-only dilation
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (dilation_w, 1))
    dilated = cv2.dilate(binary, h_kernel, iterations=1)
    
    num_labels, labels = cv2.connectedComponents(dilated)
    
    # Check which component each horizontal wire belongs to
    hw_labels = {}
    for hw in h_wires:
        mid_x = (hw["x1"] + hw["x2"]) // 2
        y = hw["y1"]
        label = labels[y, mid_x]
        hw_labels[y] = label
    
    # Check which component each individual vertical run belongs to (upper segment)
    vr_labels = {}
    for vx in ind_run_x:
        upper_segs = [vw for vw in individual_runs if vw["x1"] == vx and vw["y1"] < 300]
        if upper_segs:
            seg = upper_segs[0]
            mid_y = (seg["y1"] + seg["y2"]) // 2
            label = labels[mid_y, vx]
            vr_labels[vx] = label
    
    # How many unique component labels across all VRs?
    unique_vr_labels = set(vr_labels.values())
    
    print(f"Dilation width {dilation_w}:  total_components={num_labels}")
    print(f"  HW labels: {hw_labels}")
    print(f"  VR labels: {vr_labels}")
    print(f"  Unique VR component count: {len(unique_vr_labels)}")
    
    # For each HW, which VRs are in the same component?
    for y, hw_label in hw_labels.items():
        connected_vrs = [vx for vx, vr_label in vr_labels.items() if vr_label == hw_label]
        if connected_vrs:
            print(f"  HW y={y} → VRs: {connected_vrs}")
        else:
            print(f"  HW y={y}: NO connected VRs")
    print()

# ── Approach 2: Leftward scan from each vertical run ──
print("\n═══ Leftward scan from each vertical run ═══\n")

def scan_leftward(binary, start_x, y, max_gap=12):
    """Scan left from start_x at row y, allowing gaps. Return leftmost x reached."""
    h_img, w_img = binary.shape
    x = start_x - 1
    gap = 0
    leftmost = start_x
    while x >= 0:
        if binary[y, x] > 0:
            leftmost = x
            gap = 0
        else:
            gap += 1
            if gap > max_gap:
                break
        x -= 1
    return leftmost

for vx in ind_run_x:
    upper_segs = [vw for vw in individual_runs if vw["x1"] == vx and vw["y1"] < 300]
    if not upper_segs:
        continue
    seg = upper_segs[0]
    
    # For each y in the vertical run, scan left
    connections = []
    for y in range(seg["y1"], seg["y2"] + 1):
        leftmost = scan_leftward(binary, vx, y, max_gap=12)
        if leftmost < 260:  # reached the terminal zone
            connections.append((y, leftmost))
    
    if connections:
        # Group by y continuity
        groups = []
        cur = [connections[0]]
        for i in range(1, len(connections)):
            if connections[i][0] - connections[i-1][0] <= 3:
                cur.append(connections[i])
            else:
                groups.append(cur)
                cur = [connections[i]]
        groups.append(cur)
        
        print(f"VR x={vx}: {len(groups)} leftward connection groups")
        for g in groups:
            y_mid = (g[0][0] + g[-1][0]) // 2
            min_x = min(pt[1] for pt in g)
            closest_hw = min(h_wires, key=lambda hw: abs(hw["y1"] - y_mid))
            print(f"  y={g[0][0]}-{g[-1][0]} (mid={y_mid}) → reaches x={min_x} "
                  f"(nearest HW: y={closest_hw['y1']}, dist={abs(closest_hw['y1'] - y_mid)}px)")
    else:
        print(f"VR x={vx}: no leftward connections to terminal zone")
