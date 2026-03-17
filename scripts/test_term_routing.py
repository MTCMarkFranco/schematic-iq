"""Compute terminal→cable routing by matching terminal y-positions to HW y-positions."""
import json
import cv2
import numpy as np

# Load geometry and image
geometry = json.load(open('output/image-out-20260315-153243-stage0-geometry.json'))
discovery = json.load(open('output/image-out-20260315-153243-stage1-discovery.json'))
from cv_preprocess import compute_cable_routing_map

routing = compute_cable_routing_map('test-data/image.png', geometry, discovery['cables'])
print("HW Routing:")
for r in routing.get('routing', []):
    print(f"  HW y={r['hw_y']} -> {r['cable_label']}")

print("\nDashed regions:")
for d in geometry.get('dashed_regions', []):
    area = d['width'] * d['height']
    print(f"  ({d['x']},{d['y']}) {d['width']}x{d['height']} area={area}")

# The terminal block is at x=198,y=279,w=70,h=122 (visible from dashed regions)
# Actually look at the slider_rects and detect terminal rectangles more precisely
# For now, let's find where terminals are by scanning for text-like features
# in the RIGHT portion of the image (terminal labels like 654, 653, etc.)

# HW wires
h_wires = sorted(
    [w for w in geometry.get('wires', []) if w['orientation'] == 'horizontal'],
    key=lambda w: w['y1']
)
print("\nHorizontal wires:")
for w in h_wires:
    print(f"  y={w['y1']}: x={w['x1']}..{w['x2']} len={w['length']}")

# Terminals from discovery
terms = discovery.get('terminals', [])
print(f"\nTerminals ({len(terms)}):")
for t in terms:
    print(f"  {t['label']} block={t.get('terminal_block')}")

# The terminals are arranged top→bottom in the image:
# highest terminal number at the top, lowest at the bottom
# From the image (615x644), there are 3 groups of terminals:
# Group 1: 654-651 (top, N8000)
# Group 2: 964-961 (middle, N7888+N6000)
# Group 3: 960-957, 956-951 (bottom, N6000)
#
# HW wires: y=248, 293, 338, 382, 406
# These correspond to the 5 horizontal bus wires in the routing zone
# Each group of terminals connects to one or more of these HW wires

# The terminal block dashed region is at (198,279) 70x122
# or possibly at (137,249) width=120
# Let's check dashed regions more carefully
# Region (137,249) 120x1 is a horizontal line
# Region (137,406) 120x1 is a horizontal line
# These bracket the terminal block vertically: y=249 to y=406
# That's the full terminal block extent

# With 18 terminals between y=249 and y=406:
y_start = 249
y_end = 406
n_terms = 18
# Descending order by terminal number (highest at top)
term_labels = sorted([t['label'] for t in terms if t['label'].isdigit()],
                     key=lambda x: int(x), reverse=True)
print(f"\nTerminal labels (top→bottom): {term_labels}")

# Compute estimated y for each terminal
for i, label in enumerate(term_labels):
    frac = (i + 0.5) / n_terms
    est_y = int(y_start + frac * (y_end - y_start))
    # Find nearest HW
    nearest_hw = min(h_wires, key=lambda w: abs(w['y1'] - est_y))
    hw_y = nearest_hw['y1']
    # Find cable from routing
    cable = "?"
    for r in routing.get('routing', []):
        if r['hw_y'] == hw_y:
            cable = r['cable_label']
            break
    print(f"  Terminal {label}: est_y={est_y}, nearest HW y={hw_y} -> {cable}")
