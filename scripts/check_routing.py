"""Check terminal 963's routing in the latest output."""
import json, glob, sys

# Find the latest stage3 file
pattern = sys.argv[1] if len(sys.argv) > 1 else 'output/*-stage3-final.json'
files = sorted(glob.glob(pattern))
if not files:
    files = sorted(glob.glob('output/*-stage2-raw.json'))
path = files[-1]
print(f"Reading: {path}")

d = json.load(open(path))

# Build object lookup
obj_map = {o['system_object_id']: o for o in d['objects']}

# Find terminal 963
for o in d['objects']:
    if o.get('raw_text') == '963':
        oid = o['system_object_id']
        print(f"\nTerminal 963: {oid}")

        # Trace: terminal -> wire -> cable
        for c in d['connections']:
            if c['source_object_id'] == oid:
                wire = obj_map.get(c['target_object_id'])
                if wire and wire['object_type'] == 'WIRE':
                    print(f"  -> Wire: {wire['system_object_id']} ({wire.get('raw_text', '?')})")
                    # Find cable
                    for c2 in d['connections']:
                        if c2['source_object_id'] == wire['system_object_id'] and c2['relationship_type'] == 'WIRE_TO_CABLE':
                            cable = obj_map.get(c2['target_object_id'])
                            if cable:
                                print(f"    -> Cable: {cable['system_object_id']} ({cable.get('raw_text', '?')})")
                                print(f"    RESULT: Terminal 963 -> {cable.get('raw_text', '?')}")
        break

# Also show all terminal->cable routings for comparison
print("\n=== ALL Terminal -> Cable Routings ===")
for o in sorted(d['objects'], key=lambda x: x.get('raw_text', '')):
    if o['object_type'] != 'TERMINAL':
        continue
    oid = o['system_object_id']
    label = o.get('raw_text', '?')
    # Find wire
    for c in d['connections']:
        if c['source_object_id'] == oid and c['relationship_type'] == 'DIRECT_WIRE':
            wire = obj_map.get(c['target_object_id'])
            if wire:
                # Find cable
                for c2 in d['connections']:
                    if c2['source_object_id'] == wire['system_object_id'] and c2['relationship_type'] == 'WIRE_TO_CABLE':
                        cable = obj_map.get(c2['target_object_id'])
                        if cable:
                            print(f"  Terminal {label} -> Wire {wire.get('raw_text','?')} -> Cable {cable.get('raw_text','?')}")
