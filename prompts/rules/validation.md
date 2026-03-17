RULE VALIDATE_1:
  Every TERMINAL must participate in at least one connection
  OR be explicitly marked as unused

RULE VALIDATE_2:
  Every WIRE must connect exactly two objects

RULE VALIDATE_3:
  No object may connect to itself

RULE VALIDATE_4:
  Labels that duplicate terminal text must NOT be treated as terminals

RULE VALIDATE_5:
  Do NOT infer missing wires to "complete" a pattern