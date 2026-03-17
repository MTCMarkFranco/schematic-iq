import json

def trace_run(filepath, label):
    with open(filepath) as f:
        data = json.load(f)
    objects = {o['system_object_id']: o for o in data['objects']}
    conns = data['connections']
    
    wire_to_cable = {}
    for c in conns:
        if c['relationship_type'] == 'WIRE_TO_CABLE':
            wire_to_cable[c['source_object_id']] = c['target_object_id']
    
    # Find terminal 48
    t48_ids = [oid for oid, o in objects.items() if o.get('raw_text') == '48' and o.get('object_type') == 'TERMINAL']
    for t48_id in t48_ids:
        # Find direct wire from t48
        for c in conns:
            if c['relationship_type'] == 'DIRECT_WIRE':
                if c['source_object_id'] == t48_id or c['target_object_id'] == t48_id:
                    wire_id = c['target_object_id'] if c['source_object_id'] == t48_id else c['source_object_id']
                    wire = objects.get(wire_id, {})
                    cable_id = wire_to_cable.get(wire_id, '?')
                    cable = objects.get(cable_id, {})
                    print(f"  {label}: T48 ({t48_id}) -> Wire {wire.get('raw_text','?')} ({wire_id}) -> Cable {cable.get('raw_text','?')} ({cable_id})")

# Also show terminal 47 for comparison
def trace_term(filepath, label, term_label):
    with open(filepath) as f:
        data = json.load(f)
    objects = {o['system_object_id']: o for o in data['objects']}
    conns = data['connections']
    
    wire_to_cable = {}
    for c in conns:
        if c['relationship_type'] == 'WIRE_TO_CABLE':
            wire_to_cable[c['source_object_id']] = c['target_object_id']
    
    t_ids = [oid for oid, o in objects.items() if o.get('raw_text') == term_label and o.get('object_type') == 'TERMINAL']
    for t_id in t_ids:
        for c in conns:
            if c['relationship_type'] == 'DIRECT_WIRE':
                if c['source_object_id'] == t_id or c['target_object_id'] == t_id:
                    wire_id = c['target_object_id'] if c['source_object_id'] == t_id else c['source_object_id']
                    wire = objects.get(wire_id, {})
                    cable_id = wire_to_cable.get(wire_id, '?')
                    cable = objects.get(cable_id, {})
                    print(f"  {label}: T{term_label} ({t_id}) -> Wire {wire.get('raw_text','?')} ({wire_id}) -> Cable {cable.get('raw_text','?')} ({cable_id})")


print("=== Terminal 48 cable assignment across all runs ===")
trace_run('output/image2-out-20260313-201744-stage2-run0.json', 'Run0')
trace_run('output/image2-out-20260313-201744-stage2-run1.json', 'Run1')
trace_run('output/image2-out-20260313-201744-stage2-run2.json', 'Run2')
trace_run('output/image2-out-20260313-201744-stage2-raw.json', 'Consensus')
trace_run('output/image2-out-20260313-201744-stage3-final.json', 'Final')
trace_run('output/image2-out-20260311-164429-stage3-final.json', 'PrevRun')

print("\n=== For context: neighboring terminals 46-49 ===")
for t in ['46', '47', '48', '49']:
    print(f"\n--- Terminal {t} ---")
    trace_term('output/image2-out-20260313-201744-stage3-final.json', 'Final', t)
    trace_term('output/image2-out-20260311-164429-stage3-final.json', 'PrevRun', t)
