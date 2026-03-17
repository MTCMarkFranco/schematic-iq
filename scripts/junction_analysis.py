"""Check junction patterns at intersections of terminal wires with vertical bus lines.
Determines CONNECTED (junction dot) vs CROSSOVER (no connection) at each intersection."""
import cv2
import numpy as np
import json, glob, sys
sys.path.insert(0, ".")
from cv_preprocess import load_and_preprocess

image_path = "test-data/image.png"
img, gray, binary = load_and_preprocess(image_path)
h, w = gray.shape

# Load geometry
geo_f = sorted(glob.glob("output/*stage0-geometry.json"))[-1]
with open(geo_f) as f: geo = json.load(f)

# Key vertical bus lines (from geometry)
v_buses = [
    {"x": 190, "y1": 248, "y2": 379, "label": "V-bus-190"},
    {"x": 212, "y1": 278, "y2": 407, "label": "V-bus-212"},
    {"x": 314, "y1": 225, "y2": 557, "label": "V-bus-314"},
]

# HW wires
hw_ys = [248, 293, 338, 382, 406]

# Terminal wires (from trace_wires.py) - their Y levels where they cross the bus
term_wires = [
    {"label": "654", "cy": 42},
    {"label": "653", "cy": 65},
    {"label": "652", "cy": 87},
    {"label": "651", "cy": 109},
    {"label": "964", "cy": 249},
    {"label": "963", "cy": 272},
    {"label": "962", "cy": 294},
    {"label": "961", "cy": 316},
    {"label": "960", "cy": 339},
    {"label": "959", "cy": 361},
    {"label": "958", "cy": 383},
    {"label": "957", "cy": 406},
]

# For the v-bus at x=190 (connecting HWs y=248..379):
# Check which terminal wires intersect it and whether there's a junction dot
print("="*60)
print("Junction analysis at V-bus x=190 (y=248..379)")
print("="*60)

vx = 190
for tw in term_wires:
    ty = tw["cy"]
    label = tw["label"]
    
    # Only check if this terminal's wire reaches x=190
    # Terminal wires go from x=316 leftward. Check if there's foreground at (190, ty)
    if ty < 248 or ty > 379:  # Outside v-bus range
        continue
    
    # Check if there are foreground pixels at this point
    has_wire = binary[ty, vx] > 0
    
    if not has_wire:
        # Check nearby rows (wire might drift 1-2 pixels)
        for dy in [-1, 1, -2, 2]:
            if 0 <= ty+dy < h and binary[ty+dy, vx] > 0:
                ty_actual = ty + dy
                has_wire = True
                break
    
    if not has_wire:
        print(f"  Terminal {label} (y={ty}): NO wire at x={vx}")
        continue
    
    # Extract 11x11 window centered on intersection
    r = 5
    window = binary[max(0,ty-r):min(h,ty+r+1), max(0,vx-r):min(w,vx+r+1)]
    
    # Count foreground pixels in the window
    total_fg = np.count_nonzero(window)
    
    # Check specific directions:
    # Horizontal continuity: are there pixels going LEFT and RIGHT?
    left_pixels = np.count_nonzero(binary[max(0,ty-1):ty+2, max(0,vx-5):vx])
    right_pixels = np.count_nonzero(binary[max(0,ty-1):ty+2, vx+1:min(w,vx+6)])
    # Vertical continuity: are there pixels going UP and DOWN?
    up_pixels = np.count_nonzero(binary[max(0,ty-5):ty, max(0,vx-1):vx+2])
    down_pixels = np.count_nonzero(binary[ty+1:min(h,ty+6), max(0,vx-1):vx+2])
    
    # A junction DOT typically adds extra pixels at the crossing
    # Pure crossover: ~2-3 pixels in each direction
    # Junction: thicker blob at the center
    center_3x3 = binary[max(0,ty-1):ty+2, max(0,vx-1):vx+2]
    center_fg = np.count_nonzero(center_3x3)
    
    junction_type = "CROSSOVER"
    if center_fg >= 7:  # 3x3 mostly filled = junction dot
        junction_type = "CONNECTED (dot)"
    elif center_fg >= 5:
        junction_type = "LIKELY_CONNECTED"
    
    print(f"  Terminal {label} (y={ty}): L={left_pixels} R={right_pixels} U={up_pixels} D={down_pixels} center3x3={center_fg}  → {junction_type}")
    
    # Print the window as ASCII
    wh, ww = window.shape
    for wy in range(wh):
        row = "    "
        for wx in range(ww):
            if wy == r and wx == r:
                row += "+"  # Center
            elif window[wy, wx] > 0:
                row += "#"
            else:
                row += "."
        print(row)
    print()

# Same for v-bus x=212
print("="*60)
print("Junction analysis at V-bus x=212 (y=278..407)")
print("="*60)

vx = 212
for tw in term_wires:
    ty = tw["cy"]
    label = tw["label"]
    
    if ty < 278 or ty > 407:
        continue
    
    # Check nearby rows too
    best_ty = ty
    has_wire = binary[ty, vx] > 0
    if not has_wire:
        for dy in [-1, 1, -2, 2]:
            if 0 <= ty+dy < h and binary[ty+dy, vx] > 0:
                best_ty = ty + dy
                has_wire = True
                break
    
    if not has_wire:
        print(f"  Terminal {label} (y={ty}): NO wire at x={vx}")
        continue
    
    ty = best_ty
    r = 5
    window = binary[max(0,ty-r):min(h,ty+r+1), max(0,vx-r):min(w,vx+r+1)]
    
    left_pixels = np.count_nonzero(binary[max(0,ty-1):ty+2, max(0,vx-5):vx])
    right_pixels = np.count_nonzero(binary[max(0,ty-1):ty+2, vx+1:min(w,vx+6)])
    up_pixels = np.count_nonzero(binary[max(0,ty-5):ty, max(0,vx-1):vx+2])
    down_pixels = np.count_nonzero(binary[ty+1:min(h,ty+6), max(0,vx-1):vx+2])
    center_3x3 = binary[max(0,ty-1):ty+2, max(0,vx-1):vx+2]
    center_fg = np.count_nonzero(center_3x3)
    
    junction_type = "CROSSOVER"
    if center_fg >= 7:
        junction_type = "CONNECTED (dot)"
    elif center_fg >= 5:
        junction_type = "LIKELY_CONNECTED"
    
    print(f"  Terminal {label} (y={ty}): L={left_pixels} R={right_pixels} U={up_pixels} D={down_pixels} center3x3={center_fg}  → {junction_type}")
    
    wh, ww = window.shape
    for wy in range(wh):
        row = "    "
        for wx in range(ww):
            if wy == r and wx == r:
                row += "+"
            elif window[wy, wx] > 0:
                row += "#"
            else:
                row += "."
        print(row)
    print()

# Also check HW wires at both v-buses
print("="*60)
print("HW junction analysis at V-bus x=190")
print("="*60)
vx = 190
for hw_y in hw_ys:
    if hw_y < 248 or hw_y > 379:
        continue
    r = 5
    window = binary[max(0,hw_y-r):min(h,hw_y+r+1), max(0,vx-r):min(w,vx+r+1)]
    center_3x3 = binary[max(0,hw_y-1):hw_y+2, max(0,vx-1):vx+2]
    center_fg = np.count_nonzero(center_3x3)
    left_p = np.count_nonzero(binary[max(0,hw_y-1):hw_y+2, max(0,vx-5):vx])
    right_p = np.count_nonzero(binary[max(0,hw_y-1):hw_y+2, vx+1:min(w,vx+6)])
    up_p = np.count_nonzero(binary[max(0,hw_y-5):hw_y, max(0,vx-1):vx+2])
    down_p = np.count_nonzero(binary[hw_y+1:min(h,hw_y+6), max(0,vx-1):vx+2])
    
    junction_type = "CROSSOVER"
    if center_fg >= 7:
        junction_type = "CONNECTED (dot)"
    elif center_fg >= 5:
        junction_type = "LIKELY_CONNECTED"
    
    print(f"  HW y={hw_y}: L={left_p} R={right_p} U={up_p} D={down_p} center3x3={center_fg}  → {junction_type}")
    wh, ww = window.shape
    for wy in range(wh):
        row = "    "
        for wx in range(ww):
            if wy == r and wx == r:
                row += "+"
            elif window[wy, wx] > 0:
                row += "#"
            else:
                row += "."
        print(row)
    print()

print("="*60)
print("HW junction analysis at V-bus x=212")
print("="*60)
vx = 212
for hw_y in hw_ys:
    if hw_y < 278 or hw_y > 407:
        continue
    r = 5
    window = binary[max(0,hw_y-r):min(h,hw_y+r+1), max(0,vx-r):min(w,vx+r+1)]
    center_3x3 = binary[max(0,hw_y-1):hw_y+2, max(0,vx-1):vx+2]
    center_fg = np.count_nonzero(center_3x3)
    left_p = np.count_nonzero(binary[max(0,hw_y-1):hw_y+2, max(0,vx-5):vx])
    right_p = np.count_nonzero(binary[max(0,hw_y-1):hw_y+2, vx+1:min(w,vx+6)])
    up_p = np.count_nonzero(binary[max(0,hw_y-5):hw_y, max(0,vx-1):vx+2])
    down_p = np.count_nonzero(binary[hw_y+1:min(h,hw_y+6), max(0,vx-1):vx+2])
    
    junction_type = "CROSSOVER"
    if center_fg >= 7:
        junction_type = "CONNECTED (dot)"
    elif center_fg >= 5:
        junction_type = "LIKELY_CONNECTED"
    
    print(f"  HW y={hw_y}: L={left_p} R={right_p} U={up_p} D={down_p} center3x3={center_fg}  → {junction_type}")
    wh, ww = window.shape
    for wy in range(wh):
        row = "    "
        for wx in range(ww):
            if wy == r and wx == r:
                row += "+"
            elif window[wy, wx] > 0:
                row += "#"
            else:
                row += "."
        print(row)
    print()
