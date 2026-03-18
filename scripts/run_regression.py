#!/usr/bin/env python
"""
Regression test runner — compares pipeline outputs against golden files.

Usage:
    python scripts/run_regression.py --suite smoke
    python scripts/run_regression.py --suite smoke --strict
    python scripts/run_regression.py --update-golden
    python scripts/run_regression.py --help
"""

import argparse
import json
import os
import re
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.testing.golden import (
    compare_outputs,
    list_fixtures,
    load_golden,
    normalize_for_comparison,
)
from services.testing.snapshot import update_golden_from_output

GOLDEN_DIR = os.path.join("test-data", "golden")
OUTPUT_DIR = "output"

# Matches output files: <fixture>-out-<YYYYMMDD>-<HHMMSS>-<stage>.json
_OUTPUT_RE = re.compile(
    r"^(?P<fixture>.+?)-out-(?P<ts>\d{8}-\d{6})-(?P<stage>stage\d+-\w+)\.json$"
)

# Matches golden files: golden-<fixture>-<stage>.json
_GOLDEN_RE = re.compile(
    r"^golden-(?P<fixture>.+?)-(?P<stage>stage\d+-\w+)\.json$"
)


def _parse_output_filename(name: str) -> tuple[str, str, str] | None:
    """Parse a pipeline output filename into (fixture, timestamp, stage)."""
    m = _OUTPUT_RE.match(name)
    if m:
        return m.group("fixture"), m.group("ts"), m.group("stage")
    return None


def _parse_golden_filename(name: str) -> tuple[str, str] | None:
    """Parse a golden filename into (fixture, stage)."""
    m = _GOLDEN_RE.match(name)
    if m:
        return m.group("fixture"), m.group("stage")
    return None


def find_golden_pairs(fixture_filter: str | None = None) -> list[tuple[str, str]]:
    """Find pairs of (output_file, golden_file) for comparison.

    Golden files are named ``golden-<fixture>-<stage>.json``.
    Output files are named ``<fixture>-out-<timestamp>-<stage>.json``.
    Matches by fixture name + stage.  When multiple output timestamps
    exist for the same fixture+stage, the latest one is used.

    Args:
        fixture_filter: If provided, only include this fixture name.
    """
    pairs = []
    if not os.path.isdir(GOLDEN_DIR):
        return pairs

    # Index golden files by (fixture, stage)
    golden_by_key: dict[tuple[str, str], str] = {}
    for name in os.listdir(GOLDEN_DIR):
        parsed = _parse_golden_filename(name)
        if parsed:
            golden_by_key[parsed] = name

    # Index output files by (fixture, stage), keeping latest timestamp
    output_by_key: dict[tuple[str, str], str] = {}
    for name in os.listdir(OUTPUT_DIR):
        parsed = _parse_output_filename(name)
        if parsed:
            fixture, ts, stage = parsed
            key = (fixture, stage)
            existing = output_by_key.get(key)
            if existing is None or ts > _parse_output_filename(existing)[1]:
                output_by_key[key] = name

    # Build pairs where fixture+stage match
    for key in sorted(golden_by_key):
        fixture, stage = key
        if fixture_filter and fixture != fixture_filter:
            continue
        if key in output_by_key:
            pairs.append((
                os.path.join(OUTPUT_DIR, output_by_key[key]),
                os.path.join(GOLDEN_DIR, golden_by_key[key]),
            ))

    return pairs


def run_smoke_suite(strict: bool = False, log_level: str = "warning",
                    fixture_filter: str | None = None) -> bool:
    """Run the smoke regression suite.

    Compares existing output files against golden files.
    Does NOT re-run the pipeline (that requires API keys and images).

    Args:
        strict: If True, require byte-for-byte match after normalization.
        log_level: Logging verbosity.
        fixture_filter: If provided, only compare this fixture.

    Returns:
        True if all comparisons pass.
    """
    pairs = find_golden_pairs(fixture_filter=fixture_filter)

    if not pairs:
        print("⚠  No golden/output pairs found.")
        print(f"   Golden dir: {GOLDEN_DIR}")
        print(f"   Output dir: {OUTPUT_DIR}")
        print()
        print("   To create golden files from current outputs:")
        print("     python scripts/run_regression.py --update-golden")
        return True  # No pairs = nothing to fail

    all_pass = True
    for output_path, golden_path in pairs:
        fixture_name = os.path.basename(golden_path)
        print(f"  Comparing: {fixture_name}")

        try:
            with open(output_path) as f:
                actual = json.load(f)
            golden = load_golden(golden_path)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"    ✗ Error loading: {e}")
            all_pass = False
            continue

        diffs = compare_outputs(actual, golden)

        if not diffs:
            print(f"    ✔ PASS")
        else:
            if strict:
                print(f"    ✗ FAIL — {len(diffs)} differences:")
                for d in diffs[:10]:
                    print(f"      - {d}")
                if len(diffs) > 10:
                    print(f"      ... and {len(diffs) - 10} more")
                all_pass = False
            else:
                # Non-strict: just warn about structural differences
                structural = [d for d in diffs if "missing" in d or "extra" in d or "type mismatch" in d]
                if structural:
                    print(f"    ⚠ {len(structural)} structural differences (non-strict)")
                    for d in structural[:5]:
                        print(f"      - {d}")
                    all_pass = False
                else:
                    print(f"    ✔ PASS (with {len(diffs)} value-level diffs)")

    return all_pass


def main():
    parser = argparse.ArgumentParser(
        description="Schematic-IQ regression test runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_regression.py --suite smoke
  python scripts/run_regression.py --suite smoke --strict
  python scripts/run_regression.py --update-golden
        """,
    )
    parser.add_argument(
        "--suite",
        choices=["smoke"],
        default="smoke",
        help="Test suite to run (default: smoke)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require exact match after normalization",
    )
    parser.add_argument(
        "--update-golden",
        action="store_true",
        help="Update golden files from current output directory",
    )
    parser.add_argument(
        "--fixture",
        default=None,
        help="Only compare this fixture name (e.g. 'schematic-section-1')",
    )
    parser.add_argument(
        "--log-level",
        default="warning",
        choices=["debug", "info", "warning", "error"],
        help="Log verbosity (default: warning)",
    )

    args = parser.parse_args()

    if args.update_golden:
        print("Updating golden files from output/...")
        created = update_golden_from_output()
        for path in created:
            print(f"  ✔ {path}")
        print(f"\n{len(created)} golden files created/updated.")
        return

    print(f"═══ Schematic-IQ Regression Suite: {args.suite} ═══\n")

    passed = run_smoke_suite(strict=args.strict, log_level=args.log_level,
                              fixture_filter=args.fixture)

    print()
    if passed:
        print("═══ RESULT: PASS ═══")
    else:
        print("═══ RESULT: FAIL ═══")
        sys.exit(1)


if __name__ == "__main__":
    main()
