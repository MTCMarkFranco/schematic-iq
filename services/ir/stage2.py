"""
Stage 2 IR — Typed intermediate representations for LLM discovery output.

These dataclasses define the contract for Stage 2 output, enabling
typed access and validation without changing computation.
"""

from dataclasses import dataclass, field


@dataclass
class Component:
    """A discovered schematic component (relay, device box, etc.)."""
    label: str
    position: str = ""
    left_side_labels: list[str] = field(default_factory=list)
    right_side_terminals: list[str] = field(default_factory=list)


@dataclass
class Cable:
    """A discovered cable label (circle in schematic)."""
    label: str
    position: str = ""
    adjacent_labels: list[str] = field(default_factory=list)
    off_page_connector: str | None = None


@dataclass
class Terminal:
    """A discovered terminal block entry."""
    label: str
    position: str = ""
    terminal_block: str = ""
    has_slider: bool = False


@dataclass
class Stage2Output:
    """Complete Stage 2 IR — LLM discovery result."""
    components: list[Component] = field(default_factory=list)
    cables: list[Cable] = field(default_factory=list)
    terminals: list[Terminal] = field(default_factory=list)
    wire_labels: list[str] = field(default_factory=list)
    other_symbols: list[str] = field(default_factory=list)
    partition_labels: list[str] = field(default_factory=list)
    has_crossovers: bool = False
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Stage2Output":
        """Create Stage2Output from a raw discovery dict."""
        components = [
            Component(**c) if isinstance(c, dict) else Component(label=str(c))
            for c in data.get("components", [])
        ]
        cables = [
            Cable(**c) if isinstance(c, dict) else Cable(label=str(c))
            for c in data.get("cables", [])
        ]
        terminals = [
            Terminal(**t) if isinstance(t, dict) else Terminal(label=str(t))
            for t in data.get("terminals", [])
        ]

        return cls(
            components=components,
            cables=cables,
            terminals=terminals,
            wire_labels=data.get("wire_labels", []),
            other_symbols=data.get("other_symbols", []),
            partition_labels=data.get("partition_labels", []),
            has_crossovers=data.get("has_crossovers", False),
            notes=data.get("notes", ""),
        )

    def to_dict(self) -> dict:
        """Serialize back to the standard discovery dict format."""
        return {
            "components": [
                {
                    "label": c.label,
                    "position": c.position,
                    "left_side_labels": c.left_side_labels,
                    "right_side_terminals": c.right_side_terminals,
                }
                for c in self.components
            ],
            "cables": [
                {
                    "label": c.label,
                    "position": c.position,
                    "adjacent_labels": c.adjacent_labels,
                    "off_page_connector": c.off_page_connector,
                }
                for c in self.cables
            ],
            "terminals": [
                {
                    "label": t.label,
                    "position": t.position,
                    "terminal_block": t.terminal_block,
                    "has_slider": t.has_slider,
                }
                for t in self.terminals
            ],
            "wire_labels": self.wire_labels,
            "other_symbols": self.other_symbols,
            "partition_labels": self.partition_labels,
            "has_crossovers": self.has_crossovers,
            "notes": self.notes,
        }
