# Stage 3 Policy Pack

## Deterministic Extraction Rules

These rules MUST be followed by the extraction agent:

### JSON Schema Constraints
- Output must contain exactly three top-level keys: `objects`, `connections`, `partition_memberships`
- Every object must have `system_object_id` (format: OBJ1, OBJ2, ...), `object_type`, and `raw_text`
- Every connection must have `connection_id` (format: C1, C2, ...), `source_object_id`, `target_object_id`, `relationship_type`

### Object Type Rules
- `TERMINAL`: rectangle visual form, has_slider boolean, bbox coordinates
- `WIRE`: line visual form, route_segments array, terminal_label, cable_label
- `CABLE_LABEL`: circle visual form, center point, radius
- `OFF_PAGE_CONNECTOR`: circle visual form, center point, radius
- `SYMBOLIC_COMPONENT`: variable visual form

### Relationship Type Rules
- `DIRECT_WIRE`: Terminal-to-wire connection
- `WIRE_TO_CABLE`: Wire connects to cable label
- `CABLE_TO_CONNECTOR`: Cable connects to off-page connector
- `JUMPER_SHORT`: Two terminals share a jumper connection
- `PIN_OF`: Component pin relationship
- `ANNOTATES`: Label annotation

### Code Interpreter Rules
- Always use OpenCV for wire tracing — do not estimate wire routes visually
- Load the uploaded geometry JSON for authoritative wire coordinates
- Use morphological operations to distinguish BEND (connection) from STRAIGHT (crossover) at bus line intersections
- Verify all terminal labels against the discovery inventory
