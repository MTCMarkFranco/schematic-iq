"""Diagnostic: analyze wire routing topology for the test image."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cv_preprocess import extract_geometry, load_binary_image
import numpy as np

IMAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test-data", "image.png")

geom = extract_geometry(IMAGE)
_, binary = load_binary_image(IMAGE)
h, w = binary.shape
scale = geom.get("scale", 1.0)

h_wires = sorted([w2 for w2 in geom["wires"] if w2["orientation"] == "horizontal"], key=lambda w2: w2["y1"])
v_wires = sorted([w2 for w2 in geom["wires"] if w2["orientation"] == "vertical"], key=lambda w2: w2["x1"])

# Identify bus lines vs individual wire runs
max_vlen = max(vw["length"] for vw in v_wires)
bus_threshold = max_vlen * 0.85
bus_lines = sorted([vw for vw in v_wires if vw["length"] >= bus_threshold], key=lambda vw: vw["x1"])
individual_runs = sorted([vw for vw in v_wires if vw["length"] < bus_threshold and vw["length"] > 80], key=lambda vw: vw["x1"])

print(f"Image: {geom['image_size']['width']}x{geom['image_size']['height']}")
print(f"\nBus lines: {[(bl['x1'], bl['length']) for bl in bus_lines]}")
print(f"Individual runs: {[(vw['x1'], vw['y1'], vw['y2'], vw['length']) for vw in individual_runs]}")

# ── Part 1: For each horizontal wire, trace rightward through the gap ────
print("\n═══ PART 1: Wire path tracing from terminal side into routing zone ═══\n")
for hw in h_wires:
    y = hw["y1"]
    x_start = hw["x2"]  # right endpoint
    print(f"HW y={y} (x={hw['x1']}→{x_start}):")
    
    # Scan rightward from the HW endpoint looking for foreground pixels
    scan_band = 3  # ±3 pixels in y
    path_x = []
    for x in range(x_start, min(w, x_start + 200)):
        # Check if there are foreground pixels at this x column near y
        y_lo = max(0, y - scan_band)
        y_hi = min(h, y + scan_band + 1)
        col = binary[y_lo:y_hi, x]
        if np.any(col > 0):
            path_x.append(x)
    
    if path_x:
        # Find where the path reaches each individual vertical run
        reached_runs = []
        for vw in individual_runs:
            vx = vw["x1"]
            if any(abs(px - vx) <= 3 for px in path_x):
                reached_runs.append(vx)
        max_x = max(path_x) if path_x else x_start
        gaps = []
        prev = path_x[0]
        for px in path_x[1:]:
            if px - prev > 2:
                gaps.append((prev, px))
            prev = px
        gap_str = f"  gaps at: {gaps}" if gaps else "  continuous"
        print(f"  Path extends rightward to x={max_x} ({max_x-x_start}px past HW end)")
        print(f"  {gap_str}")
        print(f"  Reaches vertical runs at x={reached_runs}")
    else:
        print(f"  NO foreground pixels past x={x_start}")

# ── Part 2: For each individual vertical run, trace downward to see where it goes ────
print("\n═══ PART 2: Where does each vertical run terminate? ═══\n")
for vw in individual_runs:
    vx = vw["x1"]
    y_end = vw["y2"]
    # Scan below (and above) the vertical run for continuations
    scan_band = 3
    below_path = []
    for y in range(y_end, min(h, y_end + 200)):
        x_lo = max(0, vx - scan_band)
        x_hi = min(w, vx + scan_band + 1)
        row = binary[y, x_lo:x_hi]
        if np.any(row > 0):
            below_path.append(y)
    
    # Check for horizontal branches from the bottom of the vertical
    bottom_y = max(below_path) if below_path else y_end
    # Scan horizontally at several y positions near the bottom
    print(f"VW x={vx} (y={vw['y1']}→{vw['y2']}):")
    if below_path:
        print(f"  Continues below to y={bottom_y}")
    else:
        print(f"  Terminates at y={y_end}")

# ── Part 3: Scan cable circle regions ────
print("\n═══ PART 3: Cable circle positions (detect circles in binary) ═══\n")
import cv2

# Use HoughCircles to find cable circles
gray, _ = load_binary_image(IMAGE)
# Actually load the gray image properly
img = cv2.imread(IMAGE)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
                           param1=100, param2=30, minRadius=10, maxRadius=50)

if circles is not None:
    circles = np.round(circles[0, :]).astype("int")
    for (cx, cy, r) in circles:
        print(f"  Circle at ({cx}, {cy}) radius={r}")
else:
    print("  No circles detected")

# ── Part 4: Flood-fill based connectivity from each horizontal wire ────
print("\n═══ PART 4: Flood-fill connectivity from each HW endpoint ═══\n")

def directional_trace(binary, start_x, start_y, direction="right", max_steps=500):
    """Follow foreground pixels in the binary image with direction preference.
    Returns list of (x,y) waypoints and final position."""
    h, w = binary.shape
    path = [(start_x, start_y)]
    x, y = start_x, start_y
    visited = set()
    visited.add((x, y))
    
    for _ in range(max_steps):
        # Define neighbor priorities based on current direction
        if direction == "right":
            neighbors = [(x+1, y), (x+1, y-1), (x+1, y+1), (x, y-1), (x, y+1)]
        elif direction == "left":
            neighbors = [(x-1, y), (x-1, y-1), (x-1, y+1), (x, y-1), (x, y+1)]
        elif direction == "down":
            neighbors = [(x, y+1), (x-1, y+1), (x+1, y+1), (x-1, y), (x+1, y)]
        elif direction == "up":
            neighbors = [(x, y-1), (x-1, y-1), (x+1, y-1), (x-1, y), (x+1, y)]
        
        moved = False
        for nx, ny in neighbors:
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                if binary[ny, nx] > 0:
                    visited.add((nx, ny))
                    # Update direction based on movement
                    dx, dy = nx - x, ny - y
                    if abs(dx) > abs(dy):
                        direction = "right" if dx > 0 else "left"
                    elif abs(dy) > abs(dx):
                        direction = "down" if dy > 0 else "up"
                    x, y = nx, ny
                    path.append((x, y))
                    moved = True
                    break
        
        if not moved:
            break
    
    return path

for hw in h_wires:
    start_x = hw["x2"] + 1
    start_y = hw["y1"]
    path = directional_trace(binary, start_x, start_y, "right")
    if path:
        final_x, final_y = path[-1]
        # Find which vertical runs the path passes through
        path_x_set = set(p[0] for p in path)
        reached = [vw["x1"] for vw in individual_runs if any(abs(px - vw["x1"]) <= 2 for px in path_x_set)]
        # Find rightmost x and final region
        max_x = max(p[0] for p in path)
        max_y = max(p[1] for p in path)
        print(f"HW y={hw['y1']}: traced {len(path)} steps → final ({final_x},{final_y}), "
              f"max_x={max_x}, max_y={max_y}, reached runs: {reached}")
    else:
        print(f"HW y={hw['y1']}: no trace")
