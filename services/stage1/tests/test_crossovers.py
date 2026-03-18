"""
Unit tests for crossover detection and wire-to-wire crossing logic.

Tests use synthetic scenarios to verify that the system can distinguish
between wire crossovers (wires passing over each other) and wire joins
(wires that actually connect at an intersection).
"""

import numpy as np
import pytest

from services.geometry_extraction_service import build_wire_chains


class TestCrossoverVsJoin:
    """Tests for distinguishing crossovers from joins in wire geometry."""

    def test_perpendicular_crossing_at_midpoints_separate(self):
        """Two perpendicular wires crossing at midpoints should NOT chain.

        The chain builder only connects wires via endpoint proximity or
        T-junction (endpoint near segment body). Wires that cross in the
        middle without endpoint contact stay separate.
        """
        wires = [
            {"x1": 0, "y1": 100, "x2": 200, "y2": 100, "orientation": "horizontal"},
            {"x1": 100, "y1": 0, "x2": 100, "y2": 200, "orientation": "vertical"},
        ]
        chains = build_wire_chains(wires, join_radius=15)
        # No endpoint is near the other wire's body — these are separate
        assert len(chains) == 2

    def test_parallel_non_touching_separate(self):
        """Two parallel wires that don't touch should be separate chains."""
        wires = [
            {"x1": 0, "y1": 50, "x2": 200, "y2": 50, "orientation": "horizontal"},
            {"x1": 0, "y1": 150, "x2": 200, "y2": 150, "orientation": "horizontal"},
        ]
        chains = build_wire_chains(wires, join_radius=15)
        assert len(chains) == 2

    def test_two_vertical_buses_with_crossing_wire(self):
        """When a wire crosses two bus lines at their midpoints, all stay separate.

        No endpoint is near any other wire's body.
        """
        # Two vertical bus lines and one horizontal wire crossing both
        wires = [
            {"x1": 50, "y1": 0, "x2": 50, "y2": 300, "orientation": "vertical"},    # Bus 1
            {"x1": 150, "y1": 0, "x2": 150, "y2": 300, "orientation": "vertical"},   # Bus 2
            {"x1": 0, "y1": 100, "x2": 200, "y2": 100, "orientation": "horizontal"},  # Wire crossing both
        ]
        chains = build_wire_chains(wires, join_radius=15)
        # All separate — endpoints are far from other wires' bodies
        assert len(chains) == 3


class TestBusLineTap:
    """Tests for bus line tap detection scenarios."""

    def test_wire_taps_into_bus(self):
        """A horizontal wire meeting a vertical bus should form one chain."""
        wires = [
            {"x1": 100, "y1": 0, "x2": 100, "y2": 400, "orientation": "vertical"},   # Bus
            {"x1": 100, "y1": 200, "x2": 300, "y2": 200, "orientation": "horizontal"},  # Wire tapping bus
        ]
        chains = build_wire_chains(wires, join_radius=15)
        assert len(chains) == 1

    def test_multiple_taps_same_bus(self):
        """Multiple horizontal wires tapping into the same vertical bus."""
        wires = [
            {"x1": 100, "y1": 0, "x2": 100, "y2": 500, "orientation": "vertical"},
            {"x1": 100, "y1": 100, "x2": 300, "y2": 100, "orientation": "horizontal"},
            {"x1": 100, "y1": 200, "x2": 300, "y2": 200, "orientation": "horizontal"},
            {"x1": 100, "y1": 300, "x2": 300, "y2": 300, "orientation": "horizontal"},
        ]
        chains = build_wire_chains(wires, join_radius=15)
        # All connected through the bus
        assert len(chains) == 1
        assert len(chains[0]) == 4

    def test_wire_stops_at_bus(self):
        """A wire that ends at the bus line should connect."""
        wires = [
            {"x1": 200, "y1": 0, "x2": 200, "y2": 400, "orientation": "vertical"},
            {"x1": 50, "y1": 150, "x2": 200, "y2": 150, "orientation": "horizontal"},
        ]
        chains = build_wire_chains(wires, join_radius=15)
        assert len(chains) == 1

    def test_wire_crosses_bus_no_endpoint_contact(self):
        """A horizontal wire passing through a vertical bus without endpoint contact stays separate."""
        wires = [
            {"x1": 200, "y1": 0, "x2": 200, "y2": 400, "orientation": "vertical"},
            {"x1": 50, "y1": 200, "x2": 350, "y2": 200, "orientation": "horizontal"},
        ]
        chains = build_wire_chains(wires, join_radius=15)
        # Endpoints (50,200) and (350,200) are far from the bus at x=200
        assert len(chains) == 2
