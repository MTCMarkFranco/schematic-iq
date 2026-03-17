RULE SPATIAL_1:
  LEFT or TOP side = INPUT
  RIGHT or BOTTOM side = OUTPUT

RULE SPATIAL_2:
  Wires must connect to the midpoint of the terminal short side

RULE SPATIAL_3:
  If a line touches a terminal anywhere other than midpoint of short side
  → NOT a valid connection
``