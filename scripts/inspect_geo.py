"""Quick inspection of geometry and discovery data for terminal→HW mapping."""
import json, sys
sys.path.insert(0, ".")

# Load geometry
import glob
geo_files = sorted(glob.glob("output/*stage0-geometry.json"))
disc_files = sorted(glob.glob("output/*stage1-discovery.json"))
if not geo_files or not disc_files:
    print("No output files found"); sys.exit(1)
print(f"Using: {geo_files[-1]}, {disc_files[-1]}")
with open(geo_files[-1]) as f:
    geo = json.load(f)
with open(disc_files[-1]) as f:
    disc = json.load(f)

# Horizontal wires sorted by y
h_wires = sorted([w for w in geo["wires"] if w["orientation"] == "horizontal"], key=lambda w: w["y1"])
print("=== Horizontal Wires ===")
for w in h_wires:
    print(f"  HW y={w['y1']:4d}  x={w['x1']:4d}..{w['x2']:4d}  len={w['x2']-w['x1']}")

# Slider rects
print("\n=== Slider Rects ===")
for s in geo.get("slider_rects", []):
    print(f"  x={s['x']}, y={s['y']}, w={s['width']}, h={s['height']}, slider={s.get('has_slider', False)}")

# Dashed regions
print("\n=== Dashed Regions ===")
for d in sorted(geo["dashed_regions"], key=lambda r: r["y"]):
    area = d["width"] * d["height"]
    print(f"  x={d['x']}, y={d['y']}, w={d['width']}, h={d['height']}  area={area}")

# Discovery terminals
print("\n=== Discovery Terminals ===")
terms = disc.get("terminals", [])
for t in terms:
    label = t.get("label", "?")
    pos = t.get("position", "?")
    slider = t.get("has_slider", False)
    print(f"  {label:6s}  pos={pos:25s}  slider={slider}")

# Discovery cables
print("\n=== Discovery Cables ===")
cables = disc.get("cables", [])
for c in cables:
    if isinstance(c, dict):
        print(f"  {c.get('label','?'):10s}  pos={c.get('position','?')}")
    else:
        print(f"  {c}")
