"""
Stage 2 cable-terminal mapping utilities.
"""


def get_cable_terminal_map(discovery: dict) -> dict[str, list[str]]:
    """Build a mapping of cable labels to their associated terminals.

    Uses the terminal_block and adjacent_labels to infer cable-terminal relationships.
    """
    cable_map: dict[str, list[str]] = {}
    for cable in discovery.get("cables", []):
        if isinstance(cable, dict):
            cable_map[cable["label"]] = cable.get("adjacent_labels", [])
    return cable_map


def get_off_page_connectors(discovery: dict) -> dict[str, str | None]:
    """Extract cable -> off-page connector mapping."""
    return {
        c["label"]: c.get("off_page_connector")
        for c in discovery.get("cables", [])
        if isinstance(c, dict)
    }
