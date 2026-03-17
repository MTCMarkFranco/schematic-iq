OBJECT CABLE:
  Shape = circle (primary form)
  Label = text inside the circle
  Represents a bundle of wires

RULE CABLE_1:
  A cable does NOT directly connect to another cable

RULE CABLE_2:
  A cable must connect to terminals via WIRES

RULE CABLE_3:
  A cable may reference a remote rack or location via adjacent text or symbol

RULE CABLE_4 (IGNORE CONDUCTOR-COUNT LABELS):
  Conductor-count labels (e.g. "4C", "12C", "NC") printed near cable
  circles are drafting annotations. Ignore them entirely — do NOT
  create objects, connections, or constraints from these labels.
  They are irrelevant for wire tracing and extraction purposes.