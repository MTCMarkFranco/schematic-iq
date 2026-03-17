RULE GLOBAL_1:
  Treat the diagram as a physical electrical schematic intended for human electricians.
  Prefer visual-spatial consistency over textual inference.

RULE GLOBAL_2:
  Do NOT invent objects, labels, or connections not explicitly visible.
  If confidence < threshold, emit "unknown" rather than hallucinating.

RULE GLOBAL_3:
  Reason incrementally:
    1) Identify CABLES and TERMINALS first
    2) Validate their structure
    3) Only then infer WIRES and CONNECTIONS

RULE GLOBAL_4:
  Never infer meaning from example labels used in prompts.
  All object identity must come from the current image only.