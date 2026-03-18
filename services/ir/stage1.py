"""
Stage 1 IR — Typed intermediate representations for OpenCV geometry output.

These dataclasses define the contract for Stage 1 output, enabling
typed access and validation without changing computation.
"""

from dataclasses import dataclass, field


@dataclass
class ImageSize:
    width: int
    height: int


@dataclass
class WireSegment:
    """A single detected wire segment from Hough line detection."""
    x1: int
    y1: int
    x2: int
    y2: int
    length: float
    angle: float
    orientation: str  # "horizontal", "vertical", "diagonal"


@dataclass
class WireChain:
    """A group of connected wire segments forming a logical wire path."""
    chain_id: int
    wire_indices: list[int]


@dataclass
class DashedRegion:
    """A detected dashed-line partition boundary."""
    x: int
    y: int
    width: int
    height: int


@dataclass
class SliderRect:
    """A detected terminal rectangle containing a slider contact."""
    x: int
    y: int
    width: int
    height: int
    has_slider: bool = True


@dataclass
class GeometrySummary:
    """Summary counts from Stage 1 extraction."""
    wires: int
    wire_chains: int
    dashed_regions: int
    slider_terminals: int


@dataclass
class Stage1Output:
    """Complete Stage 1 IR — deterministic OpenCV geometry extraction result."""
    image_size: ImageSize
    scale: float
    summary: GeometrySummary
    wires: list[WireSegment] = field(default_factory=list)
    wire_chains: list[WireChain] = field(default_factory=list)
    dashed_regions: list[DashedRegion] = field(default_factory=list)
    slider_rects: list[SliderRect] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Stage1Output":
        """Create Stage1Output from a raw geometry dict (as produced by extract_geometry)."""
        image_size = ImageSize(**data["image_size"])
        summary = GeometrySummary(**data["summary"])

        wires = [WireSegment(**w) for w in data.get("wires", [])]
        chains = [WireChain(**c) for c in data.get("wire_chains", [])]
        dashed = [DashedRegion(**d) for d in data.get("dashed_regions", [])]
        sliders = [SliderRect(**s) for s in data.get("slider_rects", [])]

        return cls(
            image_size=image_size,
            scale=data.get("scale", 1.0),
            summary=summary,
            wires=wires,
            wire_chains=chains,
            dashed_regions=dashed,
            slider_rects=sliders,
        )

    def to_dict(self) -> dict:
        """Serialize back to the standard geometry dict format."""
        return {
            "image_size": {"width": self.image_size.width, "height": self.image_size.height},
            "scale": self.scale,
            "summary": {
                "wires": self.summary.wires,
                "wire_chains": self.summary.wire_chains,
                "dashed_regions": self.summary.dashed_regions,
                "slider_terminals": self.summary.slider_terminals,
            },
            "wires": [
                {
                    "x1": w.x1, "y1": w.y1, "x2": w.x2, "y2": w.y2,
                    "length": w.length, "angle": w.angle, "orientation": w.orientation,
                }
                for w in self.wires
            ],
            "wire_chains": [
                {"chain_id": c.chain_id, "wire_indices": c.wire_indices}
                for c in self.wire_chains
            ],
            "dashed_regions": [
                {"x": d.x, "y": d.y, "width": d.width, "height": d.height}
                for d in self.dashed_regions
            ],
            "slider_rects": [
                {"x": s.x, "y": s.y, "width": s.width, "height": s.height, "has_slider": s.has_slider}
                for s in self.slider_rects
            ],
        }
