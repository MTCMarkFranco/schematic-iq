TERMINAL ATTRIBUTE has_slider:
  Boolean attribute on a TERMINAL object (true / false, default false).
  Set to true when the terminal visually contains a horizontal line running
  inside the rectangle parallel to its long side, often with a dot at each end.
  A slider indicates a conditional / disconnectable path — like a fuse in place
  that can be installed or removed.
  A slider is NOT a wire, NOT a connection, and NOT a relationship.
  It is an intrinsic property of the terminal itself.
  When has_slider is true the terminal may be physically disconnected (slider
  removed) without affecting any other wiring.