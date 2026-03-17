import json
d = json.load(open("output/image-out-20260314-094017-stage2-raw.json"))
for o in d["objects"]:
    if o["object_type"] == "TERMINAL":
        print(f"  {o['system_object_id']}: {o['raw_text']}")
    elif o["object_type"] == "CABLE_LABEL":
        print(f"  {o['system_object_id']}: CABLE {o['raw_text']}")
