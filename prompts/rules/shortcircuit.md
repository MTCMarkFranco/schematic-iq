WIRE_TYPE JUMPER_WIRE:
  Connects TERMINAL to TERMINAL
  Typically outside terminal body

RULE JUMPER_1:
  A short / jumper between two adjacent terminals is shown as a small
  line segment with a FILLED DOT (bullet) at EACH end, connecting the
  OUTPUT side of one terminal to the INPUT side of the next terminal.
  These dots are distinct from wire-endpoint circles — they sit on the
  terminal block side (right side for vertical blocks) rather than on
  the cable/wire side (left side).

RULE JUMPER_2:
  A jumper does NOT replace the terminal's own cable wire.
  When terminal A has a direct wire to Cable-X AND a jumper to terminal B,
  terminal B still has its OWN independent wire to a (possibly different)
  cable. The jumper is an ADDITIONAL connection — model it as a
  JUMPER_SHORT relationship between the two terminals alongside each
  terminal's separate DIRECT_WIRE → WIRE_TO_CABLE chain.

RULE JUMPER_3:
  When you detect dots/bullets on the right side of adjacent terminals,
  look for a short connecting line between them. If present, create a
  JUMPER_SHORT connection AND still trace each terminal's independent
  wire on the left (input) side back to its own cable.

RULE JUMPER_4 (EXHAUSTIVE SCAN — CRITICAL):
  Scan EVERY adjacent terminal pair in a terminal block for jumper dots,
  not just the ones that have cable wires on their input side.
  Terminals below the last cable-wired terminal (e.g. unused spares,
  ground terminals, or continuation terminals) can also have jumpers.
  Walk the ENTIRE terminal block from first to last terminal and check
  each adjacent pair for dot-to-dot connections on the output side.