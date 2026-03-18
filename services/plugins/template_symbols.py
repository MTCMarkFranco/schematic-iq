"""
Optional template-based symbol detector plugin.

Uses OpenCV template matching to locate known symbol templates in the
schematic image and produce candidate bounding boxes with confidence
scores.  Results can optionally enrich the Stage 2 discovery inventory.

**Off by default** — enable via config (``plugins.template_symbols.enabled = true``)
or environment variable ``SIQ_PLUGIN_TEMPLATE_SYMBOLS=1``.

Usage:
    from services.plugins.template_symbols import TemplateSymbolDetector

    detector = TemplateSymbolDetector(template_dir="templates/symbols")
    candidates = detector.detect(image_path)
    # candidates: list[SymbolCandidate]
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np


@dataclass
class SymbolCandidate:
    """A detected symbol candidate with location and confidence."""

    template_name: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_name": self.template_name,
            "bbox": {"x": self.x, "y": self.y, "w": self.width, "h": self.height},
            "confidence": round(self.confidence, 4),
            "metadata": self.metadata,
        }


class TemplateSymbolDetector:
    """Template-matching symbol detector plugin.

    Parameters
    ----------
    template_dir : str | Path
        Directory containing template images (PNG).  File stems are used
        as symbol names (e.g. ``fuse.png`` → ``fuse``).
    confidence_threshold : float
        Minimum NCC score to consider a match (0.0–1.0, default 0.75).
    nms_overlap : float
        Non-maximum suppression IoU threshold (default 0.3).
    """

    def __init__(
        self,
        template_dir: str | Path = "templates/symbols",
        confidence_threshold: float = 0.75,
        nms_overlap: float = 0.3,
    ):
        self.template_dir = Path(template_dir)
        self.confidence_threshold = confidence_threshold
        self.nms_overlap = nms_overlap
        self._templates: list[tuple[str, np.ndarray]] = []

    # -- Template loading -----------------------------------------------------

    def load_templates(self) -> int:
        """Load all PNG templates from the configured directory.

        Returns the number of templates loaded.
        """
        self._templates.clear()
        if not self.template_dir.is_dir():
            return 0
        for p in sorted(self.template_dir.glob("*.png")):
            tpl = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if tpl is not None:
                self._templates.append((p.stem, tpl))
        return len(self._templates)

    # -- Detection ------------------------------------------------------------

    def detect(self, image_path: str) -> list[SymbolCandidate]:
        """Run template matching on *image_path* and return candidates.

        Templates are loaded lazily on first call if not already loaded.
        """
        if not self._templates:
            self.load_templates()
        if not self._templates:
            return []

        img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img_gray is None:
            return []

        all_candidates: list[SymbolCandidate] = []
        for name, tpl in self._templates:
            th, tw = tpl.shape[:2]
            if th > img_gray.shape[0] or tw > img_gray.shape[1]:
                continue
            result = cv2.matchTemplate(img_gray, tpl, cv2.TM_CCOEFF_NORMED)
            locs = np.where(result >= self.confidence_threshold)
            for pt_y, pt_x in zip(*locs):
                score = float(result[pt_y, pt_x])
                all_candidates.append(
                    SymbolCandidate(
                        template_name=name,
                        x=int(pt_x),
                        y=int(pt_y),
                        width=tw,
                        height=th,
                        confidence=score,
                    )
                )

        return self._nms(all_candidates)

    # -- Non-maximum suppression ----------------------------------------------

    def _nms(self, candidates: list[SymbolCandidate]) -> list[SymbolCandidate]:
        """Greedily suppress overlapping detections per template name."""
        if not candidates:
            return []
        # Group by template name
        groups: dict[str, list[SymbolCandidate]] = {}
        for c in candidates:
            groups.setdefault(c.template_name, []).append(c)

        kept: list[SymbolCandidate] = []
        for name, group in groups.items():
            group.sort(key=lambda c: c.confidence, reverse=True)
            suppressed: list[SymbolCandidate] = []
            for c in group:
                if not any(self._iou(c, s) > self.nms_overlap for s in suppressed):
                    suppressed.append(c)
            kept.extend(suppressed)

        kept.sort(key=lambda c: (c.template_name, c.y, c.x))
        return kept

    @staticmethod
    def _iou(a: SymbolCandidate, b: SymbolCandidate) -> float:
        """Compute intersection-over-union for two bounding boxes."""
        x1 = max(a.x, b.x)
        y1 = max(a.y, b.y)
        x2 = min(a.x + a.width, b.x + b.width)
        y2 = min(a.y + a.height, b.y + b.height)
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        if inter == 0:
            return 0.0
        area_a = a.width * a.height
        area_b = b.width * b.height
        return inter / (area_a + area_b - inter)

    # -- Plugin integration ---------------------------------------------------

    @staticmethod
    def is_enabled() -> bool:
        """Check if the plugin is enabled via environment variable."""
        return os.environ.get("SIQ_PLUGIN_TEMPLATE_SYMBOLS", "").lower() in (
            "1",
            "true",
            "yes",
        )

    def enrich_discovery(
        self, discovery: dict, image_path: str
    ) -> dict:
        """Optionally enrich a Stage 2 discovery dict with detected symbols.

        Adds a ``template_symbol_candidates`` key. Does NOT modify existing
        components/terminals/cables.
        """
        candidates = self.detect(image_path)
        discovery = dict(discovery)  # shallow copy
        discovery["template_symbol_candidates"] = [c.to_dict() for c in candidates]
        return discovery
