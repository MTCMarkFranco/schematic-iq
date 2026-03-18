#!/usr/bin/env python
"""
Replay a saved pipeline run — loads artifacts and outputs the final JSON.

Usage:
    python scripts/replay_run.py --run <run_id>
    python scripts/replay_run.py --list
    python scripts/replay_run.py --run <run_id> --compare <golden_file>
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.stage3.replay import replay_run, list_runs, load_run_artifacts
from services.testing.golden import compare_outputs


def main():
    parser = argparse.ArgumentParser(
        description="Replay a saved Schematic-IQ pipeline run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--run", help="Run ID to replay")
    parser.add_argument("--list", action="store_true", help="List all saved runs")
    parser.add_argument("--compare", help="Compare replay output to a golden file")
    parser.add_argument("--output", help="Save replayed output to file")

    args = parser.parse_args()

    if args.list:
        runs = list_runs()
        if not runs:
            print("No saved runs found.")
            return
        print(f"{'Run ID':<50} {'Image':<30} {'Timestamp'}")
        print("─" * 100)
        for r in runs:
            print(f"{r.get('run_id', '?'):<50} {r.get('image_name', '?'):<30} {r.get('timestamp', '?')}")
        return

    if not args.run:
        parser.print_help()
        return

    print(f"Replaying run: {args.run}")
    result = replay_run(args.run)

    n_objs = len(result.get("objects", []))
    n_conns = len(result.get("connections", []))
    print(f"  Objects: {n_objs}")
    print(f"  Connections: {n_conns}")

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"  Saved to: {args.output}")

    if args.compare:
        with open(args.compare) as f:
            golden = json.load(f)
        diffs = compare_outputs(result, golden)
        if not diffs:
            print("  ✔ Matches golden file")
        else:
            print(f"  ✗ {len(diffs)} differences:")
            for d in diffs[:10]:
                print(f"    - {d}")

    if not args.output and not args.compare:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
