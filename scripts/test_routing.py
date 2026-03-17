"""Quick test of compute_cable_routing_map."""
import json
from cv_preprocess import extract_geometry, compute_cable_routing_map

geometry = json.load(open('output/image-out-20260315-132923-stage0-geometry.json'))
discovery = json.load(open('output/image-out-20260315-132923-stage1-discovery.json'))

result = compute_cable_routing_map('test-data/image.png', geometry, discovery['cables'])
print('Cable circles:')
for cc in result.get('cable_circles', []):
    print(f"  {cc}")
print('Boundaries:')
for b in result.get('boundaries', []):
    print(f"  {b}")
print('Routing:')
for r in result.get('routing', []):
    print(f"  HW y={r['hw_y']} -> {r['cable_label']} (dist={r['distance']}px, {r['confidence']})")
