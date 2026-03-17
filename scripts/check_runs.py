"""Check terminal 963 routing in each individual Stage 2 run."""
import json, glob

for f in sorted(glob.glob("output/image-out-20260314-094017-stage2-run*.json")):
    d = json.load(open(f))
    obj_map = {o["system_object_id"]: o for o in d["objects"]}
    t963 = [o for o in d["objects"] if o.get("raw_text", "").strip() == "963"]
    if not t963:
        print(f"{f}: 963 NOT FOUND")
        continue
    tid = t963[0]["system_object_id"]
    for c in d["connections"]:
        if c["source_object_id"] == tid and c["relationship_type"] == "DIRECT_WIRE":
            wid = c["target_object_id"]
            wire = obj_map.get(wid, {})
            for c2 in d["connections"]:
                if c2["source_object_id"] == wid and c2["relationship_type"] == "WIRE_TO_CABLE":
                    cable = obj_map.get(c2["target_object_id"], {})
                    print(f"{f}: 963 -> wire {wire.get('raw_text','?')} -> cable {cable.get('raw_text','?')}")

# Also check previous raw file
f = "output/image-out-20260314-092450-stage2-raw.json"
d = json.load(open(f))
obj_map = {o["system_object_id"]: o for o in d["objects"]}
t963 = [o for o in d["objects"] if o.get("raw_text", "").strip() == "963"]
if t963:
    tid = t963[0]["system_object_id"]
    for c in d["connections"]:
        if c["source_object_id"] == tid and c["relationship_type"] == "DIRECT_WIRE":
            wid = c["target_object_id"]
            wire = obj_map.get(wid, {})
            for c2 in d["connections"]:
                if c2["source_object_id"] == wid and c2["relationship_type"] == "WIRE_TO_CABLE":
                    cable = obj_map.get(c2["target_object_id"], {})
                    print(f"OLD RAW: 963 -> wire {wire.get('raw_text','?')} -> cable {cable.get('raw_text','?')}")

# Also check stage3-final
f = "output/image-out-20260314-094017-stage3-final.json"
d = json.load(open(f))
obj_map = {o["system_object_id"]: o for o in d["objects"]}
t963 = [o for o in d["objects"] if o.get("raw_text", "").strip() == "963"]
if t963:
    tid = t963[0]["system_object_id"]
    for c in d["connections"]:
        if c["source_object_id"] == tid and c["relationship_type"] == "DIRECT_WIRE":
            wid = c["target_object_id"]
            wire = obj_map.get(wid, {})
            for c2 in d["connections"]:
                if c2["source_object_id"] == wid and c2["relationship_type"] == "WIRE_TO_CABLE":
                    cable = obj_map.get(c2["target_object_id"], {})
                    print(f"FINAL: 963 -> wire {wire.get('raw_text','?')} -> cable {cable.get('raw_text','?')}")
