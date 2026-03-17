import json, glob, sys
sys.path.insert(0, ".")
from cv_preprocess import analyze_terminal_wires

geo = json.load(open(sorted(glob.glob("output/*stage0-geometry.json"))[-1]))
disc = json.load(open(sorted(glob.glob("output/*stage1-discovery.json"))[-1]))
result = analyze_terminal_wires("test-data/image.png", geo, disc.get("terminals", []))

for t in result.get("terminal_info", []):
    p = t["jumper_partner"] or ""
    rw = "YES" if t["has_right_wire"] else "NO"
    print(f"  {t['label']:>6s} cy={t['cy']:4d}  right_wire={rw:3s}  side={t['wire_side']:10s}  partner={p}")

print("\nJumper pairs:")
for a, b in result.get("jumper_pairs", []):
    print(f"  {a} (wired) -- {b} (jumpered)")
