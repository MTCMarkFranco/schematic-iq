"""Quick check of stage2-raw.json for wire reuse and 963 routing."""
import json, sys, glob

# Find most recent raw file
raw_files = sorted(glob.glob("output/*-stage2-raw.json"))
if not raw_files:
    print("No stage2-raw files found")
    sys.exit(1)
path = raw_files[-1]
print(f"Checking: {path}\n")

with open(path) as f:
    data = json.load(f)
objs = {o["system_object_id"]: o for o in data["objects"]}

# Cables
cables = [o for o in data["objects"] if o["object_type"] == "CABLE_LABEL"]
print("=== CABLES ===")
for c in cables:
    print(f"  {c['system_object_id']}: {c['raw_text']}")

# Terminal 963 trace
print("\n=== TERMINAL 963 TRACE ===")
t963_list = [o for o in data["objects"] if o["raw_text"] == "963"]
for t963 in t963_list:
    t963_id = t963["system_object_id"]
    print(f"  Terminal: {t963_id}")
    for c in data["connections"]:
        if c["source_object_id"] == t963_id and c["relationship_type"] == "DIRECT_WIRE":
            wire_id = c["target_object_id"]
            wire = objs.get(wire_id, {})
            print(f"  Wire: {wire_id} ({wire.get('raw_text', '?')})")
            for c2 in data["connections"]:
                if c2["source_object_id"] == wire_id and c2["relationship_type"] == "WIRE_TO_CABLE":
                    cable_id = c2["target_object_id"]
                    cable = objs.get(cable_id, {})
                    print(f"  Cable: {cable_id} ({cable.get('raw_text', '?')})")

# Wire reuse check
print("\n=== WIRE REUSE CHECK (shared wires = BAD) ===")
wires = [o for o in data["objects"] if o["object_type"] == "WIRE"]
found_shared = False
for w in wires:
    wid = w["system_object_id"]
    terminals = [c["source_object_id"] for c in data["connections"]
                 if c["target_object_id"] == wid and c["relationship_type"] == "DIRECT_WIRE"]
    cables_conn = [c["target_object_id"] for c in data["connections"]
                   if c["source_object_id"] == wid and c["relationship_type"] == "WIRE_TO_CABLE"]
    if len(terminals) > 1 or len(cables_conn) > 1:
        term_names = [objs[t]["raw_text"] for t in terminals]
        cable_names = [objs.get(c, {}).get("raw_text", "?") for c in cables_conn]
        print(f"  SHARED: {wid} ({w['raw_text']}) -> terminals={term_names}, cables={cable_names}")
        found_shared = True
if not found_shared:
    print("  None found (GOOD)")
