"""Check full connection chains for terminals 963 and 964 in latest output."""
import json, glob, sys

final_f = sorted(glob.glob("output/*stage3-final.json"))[-1]
print(f"Using: {final_f}")
with open(final_f) as f:
    data = json.load(f)

objs = data.get("objects", [])
conns = data.get("connections", [])

# Build lookup  (use system_object_id)
obj_map = {o["system_object_id"]: o for o in objs}

# Find key terminals
for obj in objs:
    raw = obj.get("raw_text", "")
    if raw in ("963", "964", "962", "961", "654", "651"):
        oid = obj["system_object_id"]
        print(f"\n{'='*60}")
        print(f"Object: {oid} — {obj.get('object_type','?')} — text={raw}")
        for k, v in obj.items():
            if k not in ("system_object_id", "object_type", "raw_text"):
                print(f"  {k}: {v}")
        # Find all connections involving this object
        for c in conns:
            if c.get("source_object_id") == oid or c.get("target_object_id") == oid:
                src = obj_map.get(c["source_object_id"], {})
                tgt = obj_map.get(c["target_object_id"], {})
                print(f"  Connection {c['connection_id']}: {c['relationship_type']}")
                print(f"    from: {c['source_object_id']} ({src.get('raw_text','?')} / {src.get('object_type','?')})")
                print(f"    to:   {c['target_object_id']} ({tgt.get('raw_text','?')} / {tgt.get('object_type','?')})")

# Show all Wire objects and their cable connections
print(f"\n{'='*60}")
print("Wire → Cable mappings:")
for obj in objs:
    if obj.get("object_type") == "WIRE":
        wire_id = obj["system_object_id"]
        wire_text = obj.get("raw_text", "?")
        # Find cable connection
        for c in conns:
            if c.get("relationship_type") == "WIRE_TO_CABLE":
                if c.get("source_object_id") == wire_id or c.get("target_object_id") == wire_id:
                    other_id = c["target_object_id"] if c["source_object_id"] == wire_id else c["source_object_id"]
                    cable = obj_map.get(other_id, {})
                    # Find which terminals connect to this wire
                    term_ids = []
                    for c2 in conns:
                        if c2.get("relationship_type") == "DIRECT_WIRE" and c2.get("target_object_id") == wire_id:
                            t = obj_map.get(c2["source_object_id"], {})
                            term_ids.append(t.get("raw_text", c2["source_object_id"]))
                        elif c2.get("relationship_type") == "DIRECT_WIRE" and c2.get("source_object_id") == wire_id:
                            t = obj_map.get(c2["target_object_id"], {})
                            term_ids.append(t.get("raw_text", c2["target_object_id"]))
                    print(f"  {wire_text} ({wire_id}) → {cable.get('raw_text','?')} ({cable.get('system_object_id','?')})")
                    print(f"    terminals: {', '.join(str(t) for t in term_ids)}")

# Also show all JUMPER connections
print(f"\n{'='*60}")
print("Jumper connections:")
jumper_count = 0
for c in conns:
    if "JUMPER" in c.get("relationship_type", ""):
        jumper_count += 1
        src = obj_map.get(c["source_object_id"], {})
        tgt = obj_map.get(c["target_object_id"], {})
        print(f"  {c['connection_id']}: {src.get('raw_text','?')} → {tgt.get('raw_text','?')} ({c['relationship_type']})")
if jumper_count == 0:
    print("  (none)")
