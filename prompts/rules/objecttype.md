OBJECT TERMINAL:
  Shape = rectangle (polygon with 4 sides)
  Label = text inside the rectangle
  Label may NOT be unique across diagram

RULE TERMINAL_1:
  The short sides of the rectangle are INPUT / OUTPUT sides

RULE TERMINAL_2:
  The long sides of the rectangle are used to connect terminals together
  (forming terminal blocks)

RULE TERMINAL_3:
  A terminal can belong to exactly one TERMINAL_BLOCK

RULE TERMINAL_4:
  Terminals may visually contain a SLIDER element — a horizontal line inside
  the rectangle parallel to the long side, often with a dot at each end.
  When present, set has_slider: true on the TERMINAL object.
  A slider indicates a conditional / disconnectable path (like a removable fuse).
  A slider is NOT a wire or connection — it is a boolean attribute of the terminal.