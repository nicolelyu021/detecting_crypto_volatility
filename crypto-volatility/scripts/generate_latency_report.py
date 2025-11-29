#!/usr/bin/env python3
"""
Generate a brief markdown latency report from load_test_report.json
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def generate_report(
    json_file: str = "load_test_report.json", output_file: str = "LATENCY_REPORT.md"
):
    """Generate a brief markdown report from load test JSON."""

    # Load JSON report
    report_path = Path(json_file)
    if not report_path.exists():
        print(f"Error: {json_file} not found. Run load_test.py first.")
        sys.exit(1)

    with open(report_path, "r") as f:
        report = json.load(f)

    # Extract data
    timestamp = datetime.fromtimestamp(report["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
    num_requests = report["num_requests"]
    success_rate = report["success_rate"]
    total_time = report["total_time"]
    rps = report["requests_per_second"]

    stats = report["latency_stats"]
    mean_ms = stats["mean"] * 1000
    median_ms = stats["median"] * 1000
    min_ms = stats["min"] * 1000
    max_ms = stats["max"] * 1000
    p95_ms = stats["p95"] * 1000
    p99_ms = stats["p99"] * 1000

    success_count = report["success_count"]
    failure_count = report["failure_count"]

    # Generate markdown
    markdown = f"""# Load Test Latency Report

**Test Date:** {timestamp}

## Test Configuration
- **Total Requests:** {num_requests} (burst/concurrent)
- **Endpoint:** POST /predict
- **Test Duration:** {total_time:.2f} seconds

## Results Summary

| Metric | Value |
|--------|-------|
| **Success Rate** | {success_rate:.1f}% ({success_count} successful, {failure_count} failed) |
| **Throughput** | {rps:.2f} requests/second |
| **Mean Latency** | {mean_ms:.2f} ms |
| **Median Latency** | {median_ms:.2f} ms |
| **P95 Latency** | {p95_ms:.2f} ms |
| **P99 Latency** | {p99_ms:.2f} ms |
| **Min Latency** | {min_ms:.2f} ms |
| **Max Latency** | {max_ms:.2f} ms |

## Latency Distribution

- **Mean:** {mean_ms:.2f} ms
- **Median:** {median_ms:.2f} ms
- **95th Percentile:** {p95_ms:.2f} ms
- **99th Percentile:** {p99_ms:.2f} ms
- **Range:** {min_ms:.2f} ms - {max_ms:.2f} ms

## Conclusion

The API successfully handled {num_requests} concurrent requests with:
- {success_rate:.1f}% success rate
- P99 latency of {p99_ms:.2f} ms
- Throughput of {rps:.2f} requests/second

{"⚠️ **Note:** Some requests failed. Check load_test_report.json for details." if failure_count > 0 else "✅ All requests succeeded."}
"""

    # Write to file
    with open(output_file, "w") as f:
        f.write(markdown)

    print(f"✅ Latency report generated: {output_file}")
    print(f"\nPreview:")
    print("=" * 60)
    print(markdown)
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate markdown latency report from load test JSON"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="load_test_report.json",
        help="Input JSON file (default: load_test_report.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="LATENCY_REPORT.md",
        help="Output markdown file (default: LATENCY_REPORT.md)",
    )

    args = parser.parse_args()
    generate_report(args.input, args.output)
