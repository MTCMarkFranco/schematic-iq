OBJECT WIRE:
  May be represented by:
    - A visible line or polyline
    - OR color labels near terminals (even if no line is drawn)

RULE WIRE_1:
  A wire always connects exactly two endpoints
  (terminal-to-terminal OR cable-to-terminal)

RULE WIRE_2:
  A wire must never terminate in empty space

RULE WIRE_3 (WIRE IDENTITY — CRITICAL):
  A wire is identified ONLY by its color label (e.g. R, W, B, BK).
  Numeric labels (1, 2, 3, 4, etc.) printed on or near wires are
  positional reference numbers used by drafters — they are NOT wire
  identifiers. Ignore them completely. Do NOT create WIRE objects
  from these numbers. Each terminal connects to exactly ONE wire,
  and that wire's raw_text is its color abbreviation.