"""
Unit tests for junction analysis — multi-wire junctions, crossovers, and joins.

Tests use synthetic wire data and small generated images to exercise the
junction logic without requiring full schematic images.
"""

import json
import numpy as np
import pytest

from services.geometry_extraction_service import (
    build_wire_chains,
    detect_wires,
    extract_wire_mask,
)


class TestBuildWireChains:
    """Tests for wire chain building logic."""

    def test_single_wire_forms_chain(self):
        """A single wire segment should form a chain of length 1."""
        wires = [{"x1": 0, "y1": 50, "x2": 100, "y2": 50, "orientation": "horizontal"}]
        chains = build_wire_chains(wires, join_radius=15)
        assert len(chains) >= 1
        # All wire indices should be covered
        covered = set()
        for c in chains:
            covered.update(c)
        assert 0 in covered

    def test_connected_wires_form_one_chain(self):
        """Two wire segments that meet should be in the same chain."""
        wires = [
            {"x1": 0, "y1": 50, "x2": 100, "y2": 50, "orientation": "horizontal"},
            {"x1": 100, "y1": 50, "x2": 200, "y2": 50, "orientation": "horizontal"},
        ]
        chains = build_wire_chains(wires, join_radius=15)
        # Should be one chain containing both wires
        assert len(chains) == 1
        assert set(chains[0]) == {0, 1}

    def test_disconnected_wires_separate_chains(self):
        """Two distant wire segments should be in separate chains."""
        wires = [
            {"x1": 0, "y1": 50, "x2": 100, "y2": 50, "orientation": "horizontal"},
            {"x1": 500, "y1": 300, "x2": 600, "y2": 300, "orientation": "horizontal"},
        ]
        chains = build_wire_chains(wires, join_radius=15)
        assert len(chains) == 2

    def test_t_junction_three_wires(self):
        """Three wires meeting at a T-junction should be in one chain."""
        # Horizontal wire and vertical wire meeting at (100, 50)
        wires = [
            {"x1": 0, "y1": 50, "x2": 100, "y2": 50, "orientation": "horizontal"},
            {"x1": 100, "y1": 50, "x2": 200, "y2": 50, "orientation": "horizontal"},
            {"x1": 100, "y1": 0, "x2": 100, "y2": 50, "orientation": "vertical"},
        ]
        chains = build_wire_chains(wires, join_radius=15)
        # All three should be connected
        assert len(chains) == 1
        assert len(chains[0]) == 3

    def test_four_way_junction(self):
        """Four wires meeting at a cross should form one chain."""
        center = 100
        wires = [
            {"x1": 0, "y1": center, "x2": center, "y2": center, "orientation": "horizontal"},
            {"x1": center, "y1": center, "x2": 200, "y2": center, "orientation": "horizontal"},
            {"x1": center, "y1": 0, "x2": center, "y2": center, "orientation": "vertical"},
            {"x1": center, "y1": center, "x2": center, "y2": 200, "orientation": "vertical"},
        ]
        chains = build_wire_chains(wires, join_radius=15)
        assert len(chains) == 1
        assert len(chains[0]) == 4

    def test_near_miss_no_junction(self):
        """Wires that are close but not touching should NOT join."""
        wires = [
            {"x1": 0, "y1": 50, "x2": 100, "y2": 50, "orientation": "horizontal"},
            {"x1": 120, "y1": 50, "x2": 220, "y2": 50, "orientation": "horizontal"},
        ]
        chains = build_wire_chains(wires, join_radius=10)
        assert len(chains) == 2

    def test_chain_indices_are_correct(self):
        """Each chain should contain the correct wire indices."""
        wires = [
            {"x1": 0, "y1": 0, "x2": 50, "y2": 0, "orientation": "horizontal"},
            {"x1": 200, "y1": 200, "x2": 250, "y2": 200, "orientation": "horizontal"},
            {"x1": 400, "y1": 400, "x2": 450, "y2": 400, "orientation": "horizontal"},
        ]
        chains = build_wire_chains(wires, join_radius=10)
        assert len(chains) == 3
        # All wire indices should be covered exactly once
        all_indices = sorted(idx for chain in chains for idx in chain)
        assert all_indices == [0, 1, 2]


class TestWireMask:
    """Tests for wire mask extraction from synthetic images."""

    def _make_wire_image(self, width=200, height=200, line_coords=None):
        """Create a synthetic binary image with thin lines."""
        img = np.zeros((height, width), dtype=np.uint8)
        if line_coords:
            import cv2
            for x1, y1, x2, y2 in line_coords:
                cv2.line(img, (x1, y1), (x2, y2), 255, 2)
        return img

    def test_horizontal_wire_extracted(self):
        """A horizontal line should produce a wire mask with content."""
        binary = self._make_wire_image(
            width=300, height=100,
            line_coords=[(10, 50, 290, 50)]
        )
        mask = extract_wire_mask(binary, kernel_len=30, dilate_size=1)
        assert mask is not None
        # The mask should have some white pixels along the wire
        assert np.sum(mask > 0) > 0

    def test_vertical_wire_extracted(self):
        """A vertical line should produce a wire mask with content."""
        binary = self._make_wire_image(
            width=100, height=300,
            line_coords=[(50, 10, 50, 290)]
        )
        mask = extract_wire_mask(binary, kernel_len=30, dilate_size=1)
        assert mask is not None
        assert np.sum(mask > 0) > 0

    def test_empty_image_no_mask(self):
        """An empty image should produce an empty/minimal wire mask."""
        binary = self._make_wire_image(width=200, height=200)
        mask = extract_wire_mask(binary, kernel_len=30, dilate_size=1)
        # Empty images should have no significant wire content
        assert np.sum(mask > 0) < 100  # Allow some noise


class TestIRValidation:
    """Tests for IR validation on synthetic data."""

    def test_valid_stage1_passes(self):
        from services.ir.stage1 import Stage1Output
        from services.ir.validate import validate_stage1

        data = {
            "image_size": {"width": 1000, "height": 800},
            "scale": 1.0,
            "summary": {"wires": 2, "wire_chains": 1, "dashed_regions": 0, "slider_terminals": 0},
            "wires": [
                {"x1": 0, "y1": 50, "x2": 100, "y2": 50, "length": 100.0, "angle": 0.0, "orientation": "horizontal"},
                {"x1": 100, "y1": 50, "x2": 200, "y2": 50, "length": 100.0, "angle": 0.0, "orientation": "horizontal"},
            ],
            "wire_chains": [{"chain_id": 0, "wire_indices": [0, 1]}],
            "dashed_regions": [],
            "slider_rects": [],
        }
        ir = Stage1Output.from_dict(data)
        issues = validate_stage1(ir)
        assert issues == []

    def test_count_mismatch_detected(self):
        from services.ir.stage1 import Stage1Output
        from services.ir.validate import validate_stage1

        data = {
            "image_size": {"width": 1000, "height": 800},
            "scale": 1.0,
            "summary": {"wires": 5, "wire_chains": 1, "dashed_regions": 0, "slider_terminals": 0},  # Wrong count
            "wires": [
                {"x1": 0, "y1": 50, "x2": 100, "y2": 50, "length": 100.0, "angle": 0.0, "orientation": "horizontal"},
            ],
            "wire_chains": [{"chain_id": 0, "wire_indices": [0]}],
            "dashed_regions": [],
            "slider_rects": [],
        }
        ir = Stage1Output.from_dict(data)
        issues = validate_stage1(ir)
        assert any("Wire count mismatch" in i for i in issues)

    def test_invalid_wire_index_detected(self):
        from services.ir.stage1 import Stage1Output
        from services.ir.validate import validate_stage1

        data = {
            "image_size": {"width": 1000, "height": 800},
            "scale": 1.0,
            "summary": {"wires": 1, "wire_chains": 1, "dashed_regions": 0, "slider_terminals": 0},
            "wires": [
                {"x1": 0, "y1": 50, "x2": 100, "y2": 50, "length": 100.0, "angle": 0.0, "orientation": "horizontal"},
            ],
            "wire_chains": [{"chain_id": 0, "wire_indices": [0, 5]}],  # Index 5 is invalid
            "dashed_regions": [],
            "slider_rects": [],
        }
        ir = Stage1Output.from_dict(data)
        issues = validate_stage1(ir)
        assert any("invalid wire index" in i for i in issues)
