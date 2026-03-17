RULE WIRE_CONN_1:
  Every WIRE must have at least two valid endpoints

RULE WIRE_CONN_2:
  A wire connecting to a terminal must respect input/output side rules

RULE WIRE_CONN_3:
  Angled line at terminal midpoint indicates second connection

RULE WIRE_CONN_4:
  Color labels near terminals represent wire identity
  even if no line is drawn

RULE WIRE_CONN_5 (INTERLEAVED CABLE WIRING — CRITICAL):
  When two or more cables are stacked vertically and their wires fan out
  to a SHARED terminal block, the wires from different cables INTERLEAVE:
    Cable-A wire R  → Terminal N
    Cable-B wire R  → Terminal N-1
    Cable-A wire W  → Terminal N-2
    Cable-B wire W  → Terminal N-3
    ... and so on.
  The same color labels repeat (R, R, W, W, B, B, BK, BK) — each
  repeated color belongs to a DIFFERENT cable. The first occurrence
  connects to the CLOSER cable; the second connects to the FARTHER cable.
  You MUST trace each wire individually to its actual cable origin.
  Do NOT assume all wires in the interleaved group go to the same cable.
  IGNORE any numeric labels (1, 2, 3, 4) near wires — these are
  drafter reference numbers, NOT wire identifiers.

RULE WIRE_CONN_6:
  When the same color label (e.g. R, W, B, BK) appears on two adjacent
  wires in an interleaved group, they are SEPARATE wires belonging to
  DIFFERENT cables. One goes to the upper cable, the other to the lower
  cable. Verify by following the actual line path, not by proximity.
  Each wire's raw_text is its color abbreviation — never a number.

RULE WIRE_CONN_7 (VERTICAL BUS LINE JUNCTION vs CROSSOVER — CRITICAL):
  The OpenCV wire geometry identifies vertical bus lines by their x-positions.
  Each bus line routes to a DIFFERENT cable. For each wire, use the
  `analyze_intersection` tool to get pixel-level BEND/STRAIGHT verdicts
  at every bus line x-position. The tool's verdicts are AUTHORITATIVE:
    - BEND (tool confirmed: wire stops on one side of bus line) → CONNECTED
      to this bus line's cable.
    - DOT (tool confirmed: junction dot detected) → CONNECTED.
    - STRAIGHT (tool confirmed: wire continues through on both sides)
      → NOT connected — wire CROSSES OVER to the next bus line.
  The wire connects to the bus line where the tool reports BEND or DOT,
  not the first or nearest one. After tracing all wires, verify a balanced
  cable split — if all wires go to one cable, re-examine your routing.