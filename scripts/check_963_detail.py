"""Detailed check of terminal 963 and 964 connections, plus jumper detection."""
import json, glob

files = sorted(glob.glob('output/*-stage3-final.json'))
path = files[-1]
print(f"Reading: {path}\n")

d = json.load(open(path))
obj_map = {o['system_object_id']: o for o in d['objects']}

# Show ALL connections involving 963 or 964
for label in ['964', '963']:
    print(f"=== Terminal {label} ===")
    obj = next((o for o in d['objects'] if o.get('raw_text') == label), None)
    if not obj:
        print(f"  NOT FOUND")
        continue
    oid = obj['system_object_id']
    print(f"  Object: {oid}, type={obj['object_type']}, slider={obj.get('has_slider')}")
    
    for c in d['connections']:
        if c['source_object_id'] == oid or c['target_object_id'] == oid:
            other_id = c['target_object_id'] if c['source_object_id'] == oid else c['source_object_id']
            other = obj_map.get(other_id, {})
            print(f"  {c['connection_id']}: {c['source_object_id']} -> {c['target_object_id']} "
                  f"[{c['relationship_type']}] "
                  f"(other: {other.get('object_type','?')} '{other.get('raw_text','?')}')")
    print()

# Check for any JUMPER_SHORT connections
print("=== ALL JUMPER_SHORT connections ===")
jumpers = [c for c in d['connections'] if c['relationship_type'] == 'JUMPER_SHORT']
if jumpers:
    for j in jumpers:
        src = obj_map.get(j['source_object_id'], {})
        tgt = obj_map.get(j['target_object_id'], {})
        print(f"  {j['connection_id']}: {src.get('raw_text','?')} -> {tgt.get('raw_text','?')}")
else:
    print("  NONE detected")

# Show cable assignment counts
print("\n=== Cable Assignment Counts ===")
cable_counts = {}
for c in d['connections']:
    if c['relationship_type'] == 'WIRE_TO_CABLE':
        cable = obj_map.get(c['target_object_id'], {})
        label = cable.get('raw_text', '?')
        cable_counts[label] = cable_counts.get(label, 0) + 1
for label, count in sorted(cable_counts.items()):
    print(f"  {label}: {count} wires")
