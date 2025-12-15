#!/usr/bin/env python3
"""Benchmark script for archcheck performance testing.

Outputs results in JSON format compatible with github-action-benchmark.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def benchmark_import_time() -> float:
    """Measure import time of archcheck package."""
    start = time.perf_counter()
    import archcheck  # noqa: F401

    return time.perf_counter() - start


def benchmark_domain_types() -> float:
    """Measure creation time of domain types."""
    from archcheck.domain.model.call_site import CallSite
    from archcheck.domain.model.location import Location

    start = time.perf_counter()
    for _ in range(10000):
        Location(file=Path("test.py"), line=1, column=0)
        CallSite(module="myapp.module", function="func", line=1, file=Path("test.py"))
    return time.perf_counter() - start


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
        }
    )

    # Domain types creation
    types_time = benchmark_domain_types()
    results.append(
        {
            "name": "Domain Types (10k iterations)",
            "unit": "seconds",
            "value": types_time,
        }
    )

    # Write results
    args.output.write_text(json.dumps(results, indent=2))
    print(f"Benchmark results written to {args.output}")
    for r in results:
        print(f"  {r['name']}: {r['value']:.4f} {r['unit']}")


if __name__ == "__main__":
    main()
