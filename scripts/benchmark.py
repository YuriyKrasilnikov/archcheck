#!/usr/bin/env python3
"""Benchmark script for archcheck performance testing.

Outputs results in JSON format compatible with github-action-benchmark.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

from archcheck.domain.events import CallEvent, Location
from archcheck.infrastructure import tracking


def benchmark_import_time() -> float:
    """Measure import time of archcheck package (already imported, measures reimport)."""
    start = time.perf_counter()
    importlib.reload(importlib.import_module("archcheck"))
    return time.perf_counter() - start


def benchmark_domain_types() -> float:
    """Measure creation time of domain types."""
    start = time.perf_counter()
    for i in range(10000):
        loc = Location(file="test.py", line=i, func="test_func")
        CallEvent(location=loc, caller=None, args=(), errors=())
    return time.perf_counter() - start


def benchmark_tracking() -> float:
    """Measure tracking overhead."""

    def target() -> int:
        total = 0
        for i in range(100):
            total += i
        return total

    tracking.start()
    start = time.perf_counter()
    target()
    elapsed = time.perf_counter() - start
    tracking.stop()
    return elapsed


def main() -> None:
    """Run benchmarks and output results."""
    parser = argparse.ArgumentParser(description="Run archcheck benchmarks")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark-results.json"),
        help="Output file for benchmark results",
    )
    args = parser.parse_args()

    results = []

    # Import time
    import_time = benchmark_import_time()
    results.append(
        {
            "name": "Import Time",
            "unit": "seconds",
            "value": import_time,
        },
    )

    # Domain types creation
    types_time = benchmark_domain_types()
    results.append(
        {
            "name": "Domain Types (10k iterations)",
            "unit": "seconds",
            "value": types_time,
        },
    )

    # Tracking overhead
    tracking_time = benchmark_tracking()
    results.append(
        {
            "name": "Tracking Overhead (100 iterations)",
            "unit": "seconds",
            "value": tracking_time,
        },
    )

    # Write results
    args.output.write_text(json.dumps(results, indent=2))
    sys.stdout.write(f"Benchmark results written to {args.output}\n")
    for r in results:
        sys.stdout.write(f"  {r['name']}: {r['value']:.4f} {r['unit']}\n")


if __name__ == "__main__":
    main()
