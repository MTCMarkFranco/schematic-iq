import json

def trace_terminals(filepath, label):
    with open(filepath) as f:
        data = json.load(f)
    objects = {o['system_object_id']: o for o in data['objects']}
    conns = data['connections']
    
    wire_to_cable = {}
    for c in conns:
        if c['relationship_type'] == 'WIRE_TO_CABLE':
            wire_to_cable[c['source_object_id']] = c['target_object_id']
    
    rows = []
    for c in conns:
        if c['relationship_type'] == 'DIRECT_WIRE':
            src_obj = objects.get(c['source_object_id'], {})
            tgt_obj = objects.get(c['target_object_id'], {})
            if src_obj.get('object_type') == 'TERMINAL':
                term_id = c['source_object_id']
                wire_id = c['target_object_id']
            elif tgt_obj.get('object_type') == 'TERMINAL':
                term_id = c['target_object_id']
                wire_id = c['source_object_id']
            else:
                continue
            term = objects[term_id]
            wire = objects.get(wire_id, {})
            cable_id = wire_to_cable.get(wire_id, '?')
            cable = objects.get(cable_id, {})
            term_num = term.get('raw_text', '?')
            try:
                sort_key = int(term_num)
            except ValueError:
                sort_key = 9999
            rows.append((sort_key, term_num, wire.get('raw_text', '?'), cable.get('raw_text', '?')))
    
    rows.sort()
    print(f"\n=== {label} ===")
    print(f"{'Terminal':>10} {'Wire':>10} {'Cable':>10}")
    print("-" * 35)
    n1609 = 0
    n2364 = 0
    for _, tnum, wtext, ctext in rows:
        marker = " <-- T48" if tnum == "48" else ""
        print(f"  T{tnum:>5}    {wtext:>6}    {ctext}{marker}")
        if "1609" in ctext:
            n1609 += 1
        elif "2364" in ctext:
            n2364 += 1
    print(f"\nCable counts: N 1609={n1609}, N 2364={n2364}")

trace_terminals('output/image2-out-20260313-201744-stage3-final.json', 'Latest run (20260313)')
trace_terminals('output/image2-out-20260311-164429-stage3-final.json', 'Previous run (20260311)')
