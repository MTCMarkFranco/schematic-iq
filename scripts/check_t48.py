import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else r'output\image2-out-20260313-213747-stage3-final.json'
data = json.load(open(path))
objs = {o['system_object_id']: o for o in data['objects']}

# Find terminal 48
t48 = [o for o in data['objects'] if o.get('raw_text') == '48']
if not t48:
    print("T48 NOT FOUND")
    sys.exit(1)

t48_id = t48[0]['system_object_id']
print(f"T48 = {t48_id}")

# Find connections involving T48
conns = [c for c in data['connections'] if c['source_object_id'] == t48_id or c['target_object_id'] == t48_id]
print(f"T48 connections ({len(conns)}):")
for c in conns:
    other_id = c['target_object_id'] if c['source_object_id'] == t48_id else c['source_object_id']
    other = objs.get(other_id, {})
    print(f"  -> {other_id}  type={other.get('object_type','')}  text={other.get('raw_text','')}")
    # If it's a wire, trace further
    if other.get('object_type') == 'WIRE':
        wire_conns = [c2 for c2 in data['connections']
                      if (c2['source_object_id'] == other_id or c2['target_object_id'] == other_id)
                      and c2 != c]
        for wc in wire_conns:
            far_id = wc['target_object_id'] if wc['source_object_id'] == other_id else wc['source_object_id']
            far = objs.get(far_id, {})
            print(f"       -> {far_id}  type={far.get('object_type','')}  text={far.get('raw_text','')}")

# Show partition memberships for T48
print("\nPartition memberships containing T48:")
for pm in data.get('partition_memberships', []):
    if t48_id in str(pm) or '48' in str(pm):
        print(json.dumps(pm, indent=2))

# Show cable labels
print("\nCable labels:")
for o in data['objects']:
    if o['object_type'] == 'CABLE_LABEL':
        print(f"  {o['system_object_id']}  text={o.get('raw_text','')}")

# Show all partition memberships
print("\nAll partition memberships:")
for pm in data.get('partition_memberships', []):
    print(json.dumps(pm, indent=2))
