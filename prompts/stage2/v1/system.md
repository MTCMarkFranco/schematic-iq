Look at this electrical schematic image and return a JSON object with these keys:

{
  "components": [
    {
      "label": "component label from the rectangular box (typically a short alphanumeric code, 2-4 characters)",
      "position": "spatial position in the image — use one of: top-left, top-center, top-right, middle-left, middle-center, middle-right, bottom-left, bottom-center, bottom-right",
      "left_side_labels": ["labels/references on the LEFT side of this component (cross-reference codes to other drawing sheets, typically in letter-letter+number or letter+number-number format)"],
      "right_side_terminals": ["polarity/wire labels on the RIGHT side (polarity prefix such as (+) or (-) followed by a standard wire color abbreviation)"]
    }
  ],
  "cables": [
    {
      "label": "text inside the larger circle (cable identifier, e.g. N8000)",
      "position": "spatial position in the image",
      "adjacent_labels": ["any text labels immediately next to this cable (panel-board designators, page or book references, rack references) — EXCLUDE conductor-count tags like 4C, 12C as they are irrelevant"],
      "off_page_connector": "text inside the smaller circle that intersects this cable circle (the off-page connector label), or null if none visible"
    }
  ],
  "terminals": [
    {
      "label": "text inside the terminal rectangle (typically a numeric or alphanumeric code like 654, 963, TB1-3)",
      "position": "spatial position in the image",
      "terminal_block": "name/label of the terminal block this terminal belongs to (e.g. TB1), or null if unclear",
      "has_slider": "true if the terminal rectangle contains an internal horizontal line/dash (often with a small dot at each end) running parallel to the long side, otherwise false. Zoom in on each terminal and inspect carefully — sliders are thin marks that are easy to miss."
    }
  ],
  "wire_labels": ["list of distinct wire/cable labels seen (polarity+color codes, conductor counts, numeric identifiers, etc.)"],
  "other_symbols": [
    {
      "text": "text inside or near the symbol",
      "shape": "shape description (e.g. 'pentagon', 'diamond', 'triangle')",
      "position": "spatial position in the image"
    }
  ],
  "partition_labels": ["any partition/boundary labels (zone or section titles found near dashed boundary lines)"],
  "has_crossovers": true/false,
  "notes": "any other relevant observations about the diagram layout"
}

INSTRUCTIONS:
- Scan the ENTIRE image systematically: left-to-right, top-to-bottom.
- **has_crossovers DETECTION (CRITICAL)**: Set `has_crossovers` to `true` if ANY of these are present:
  1. **Two or more parallel vertical lines** running between the terminal block area and the cable circles (these are vertical bus lines). If you see two vertical bus lines, crossovers are GUARANTEED — wires must cross over one bus line to reach the other.
  2. **Bumps or bridge symbols** at any wire-to-wire intersection (a small hump drawn on one wire to show it passing over another). NOTE: Do NOT confuse these with bends/curves at vertical bus line intersections — those indicate connections, not crossovers.
  3. **Multiple cables** (e.g., N 1609 and N 2364) whose wires share the same terminal block — wires from different cables will interleave and cross.
  - When in doubt, set `has_crossovers` to `true`. Under-detection causes downstream routing errors.
- COMPONENTS are individual relay/device labels (typically short alphanumeric codes) that are visually INSIDE a closed rectangular symbol (all 4 sides of the box are visible). Only classify as a component when the enclosing box is clearly present.
- Do NOT classify free text near terminals/wires as a component, even if it looks like a code.
- Left-side routing/destination strings (often long or hyphenated, e.g. A1-2 style cross-references) belong in terminal/component side labels, NOT in the components array unless the text is actually enclosed by a component rectangle.
- Do NOT list zone/section titles (longer descriptive names for areas or cabinets) as components — those are partition labels.
- For each rectangular box component, look carefully at BOTH sides:
  - LEFT side: external reference labels (cross-reference codes pointing to other drawing sheets)
  - RIGHT side: polarity markers and wire connection points (polarity prefix followed by wire color code)
- CABLES appear as circles with text inside (e.g. N8000). An off-page connector is a SMALLER circle that visually intersects/overlaps the cable circle. For each cable circle, read the cable label inside the large circle, note all adjacent text, and record the off-page connector label from any smaller intersecting circle.
- TERMINALS are small rectangles (often stacked vertically) with a number or alphanumeric code INSIDE. They form terminal blocks (e.g. TB1). Read and list EVERY terminal rectangle and its internal label.
- Terminal-only crops are valid: even if no SYMBOLIC_COMPONENT is visible nearby, still list all terminal rectangles you can see. Do not drop a terminal just because it appears unused or has no visible wire.
- WIRE LABEL OWNERSHIP RULE: Do NOT attach wire color labels to terminal objects. Keep wire/color text in top-level `wire_labels`; wire objects are created in later stages.
- IGNORE NUMERIC WIRE LABELS: Numbers (1, 2, 3, 4, etc.) printed on or near wire lines are drafter reference numbers, NOT wire identifiers. Do NOT include them in `wire_labels`. Only include color abbreviations (R, W, B, BK, etc.).
- IGNORE CONDUCTOR-COUNT LABELS: Labels like "4C", "12C", "NC" near cable circles are drafting annotations. Do NOT include them in `adjacent_labels` or `wire_labels` — they are irrelevant for extraction.
- SLIDER DETECTION (CRITICAL): For EACH terminal rectangle, zoom in and look INSIDE the rectangle body for a thin horizontal line or dash running parallel to the long side. Sliders often have a small dot or circle at each end. Not every terminal has a slider — but you MUST inspect each one individually and report `has_slider: true` for those that do. Sliders are easy to miss at low zoom — look carefully.
- Look for small symbols (pentagons, arrows, diamonds) that are NOT components or connectors.
- Look for labels near dashed lines (partition boundaries). Zone/area titles belong here.
- Be thorough — list EVERY element you can see. Missing items here means they'll be missing from the final output.

## APPLICABLE DOMAIN RULES

### Object Recognition
- **TERMINAL**: Shape is a rectangle. Label is text inside the rectangle. The short sides are INPUT/OUTPUT sides. The long sides connect terminals together to form terminal blocks. Labels may NOT be unique across the diagram.
- **CABLE**: Shape is a larger circle. Label is text inside the circle (e.g. N8000). Represents a bundle of wires. One side connects to wires, the other side connects to an off-page connector.
- **OFF_PAGE_CONNECTOR**: Shape is a smaller circle that visually intersects/overlaps with a cable circle. Label is text inside this smaller circle. Indicates where the cable goes on another page or sheet.
- **CABLE vs OFF_PAGE_CONNECTOR**: Cables are ALWAYS the larger circle. Off-page connectors are ALWAYS the smaller circle that intersects/overlaps the cable circle. They always appear as a pair.
- **TERMINAL_BLOCK**: A group of terminal objects aligned on their long sides, possibly enclosed by a larger rectangle. It is a grouping construct, not an electrical component itself.
- **RACK_REFERENCE**: May appear as text or a smaller symbol near a cable. Indicates where the other end of the cable terminates.

### Spatial Rules
- LEFT or TOP side of a terminal = INPUT side.
- RIGHT or BOTTOM side of a terminal = OUTPUT side.
- Terminals may visually contain a SLIDER element (a horizontal line inside the rectangle parallel to the long side, often with a dot at each end). This indicates a conditional/disconnectable path — note it as a terminal attribute, not a connection.

### Discipline Rules
- Treat the diagram as a physical electrical schematic intended for human electricians. Prefer visual-spatial consistency over textual inference.
- Do NOT invent objects, labels, or connections not explicitly visible. If confidence is low, emit "unknown" rather than guessing.
- Never infer meaning from example labels used in these instructions. All object identity must come from the current image only.
- If ambiguity exists, annotate uncertainty explicitly. Prefer omission over hallucination.
- Preserve original labels even if duplicated; generate internal IDs separately.