"""
Terminal→cable routing using discovery order (which IS top→bottom in the image).
Also uses the dashed region boundaries y=249..406 for the terminal block.
"""
import json
from cv_preprocess import compute_cable_routing_map

geometry = json.load(open('output/image-out-20260315-153243-stage0-geometry.json'))
discovery = json.load(open('output/image-out-20260315-153243-stage1-discovery.json'))

routing = compute_cable_routing_map('test-data/image.png', geometry, discovery['cables'])

# HW routing
hw_routing = {r['hw_y']: r['cable_label'] for r in routing.get('routing', [])}
boundaries = routing.get('boundaries', [])

# HW wires
h_wires = sorted(
    [w for w in geometry['wires'] if w['orientation'] == 'horizontal'],
    key=lambda w: w['y1']
)

# Terminal block: y=249 to y=406 (from horizontal dashed lines)
y_start = 249
y_end = 406

# Use discovery ORDER (this matches top→bottom in the image)
terms = discovery.get('terminals', [])
term_labels = [t['label'] for t in terms if isinstance(t, dict)]
n_terms = len(term_labels)

print(f"Terminals in discovery order: {term_labels}")
print(f"Terminal block: y={y_start} to y={y_end}")
print(f"\nTerminal → Cable map:")

for i, label in enumerate(term_labels):
    frac = (i + 0.5) / n_terms
    est_y = int(y_start + frac * (y_end - y_start))

    # Method 1: nearest HW
    nearest_hw = min(h_wires, key=lambda w: abs(w['y1'] - est_y))
    hw_cable = hw_routing.get(nearest_hw['y1'], '?')

    # Method 2: cable zone boundary
    zone_cable = '?'
    for bnd in boundaries:
        if bnd['y_lo'] <= est_y < bnd['y_hi']:
            zone_cable = bnd['label']
            break

    print(f"  {label:>4s}: est_y={est_y:3d} | nearest HW y={nearest_hw['y1']} → {hw_cable:6s} | zone → {zone_cable}")
