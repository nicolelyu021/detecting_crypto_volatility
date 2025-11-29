#!/usr/bin/env python3
"""
Load test script for the volatility prediction API.
Sends 100 burst requests and measures latency.
"""

import asyncio
import json
import statistics
import time
from typing import List, Dict
import httpx
import argparse


async def make_request(client: httpx.AsyncClient, url: str, payload: Dict) -> Dict:
    """Make a single request and return timing information."""
    start_time = time.time()
    try:
        response = await client.post(url, json=payload, timeout=30.0)
        latency = time.time() - start_time
        return {
            'status_code': response.status_code,
            'latency': latency,
            'success': response.status_code == 200,
            'error': None
        }
    except Exception as e:
        latency = time.time() - start_time
        return {
            'status_code': None,
            'latency': latency,
            'success': False,
            'error': str(e)
        }


async def run_load_test(base_url: str, num_requests: int = 100):
    """Run load test with burst requests."""
    print(f"Starting load test: {num_requests} requests to {base_url}/predict")
    print("=" * 60)
    
    # Sample feature payload
    payload = {
        "price": 50000.0,
        "midprice": 50000.5,
        "return_1s": 0.0001,
        "return_5s": 0.0005,
        "return_30s": 0.002,
        "return_60s": 0.004,
        "volatility": 0.001,
        "trade_intensity": 2.5,
        "spread_abs": 1.0,
        "spread_rel": 0.00002,
        "order_book_imbalance": 0.1
    }
    
    url = f"{base_url}/predict"
    results: List[Dict] = []
    
    # Create async client with connection pooling
    async with httpx.AsyncClient() as client:
        # Send all requests concurrently (burst)
        print(f"Sending {num_requests} concurrent requests...")
        start_time = time.time()
        
        tasks = [make_request(client, url, payload) for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
    
    # Analyze results
    latencies = [r['latency'] for r in results]
    successes = [r for r in results if r['success']]
    failures = [r for r in results if not r['success']]
    
    # Calculate statistics
    if latencies:
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        if len(latencies) > 1:
            stdev_latency = statistics.stdev(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        else:
            stdev_latency = 0.0
            p95_latency = latencies[0]
            p99_latency = latencies[0]
    else:
        mean_latency = median_latency = min_latency = max_latency = 0.0
        stdev_latency = p95_latency = p99_latency = 0.0
    
    success_rate = len(successes) / len(results) * 100 if results else 0.0
    requests_per_second = len(results) / total_time if total_time > 0 else 0.0
    
    # Print report
    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)
    print(f"Total Requests: {num_requests}")
    print(f"Successful: {len(successes)} ({success_rate:.1f}%)")
    print(f"Failed: {len(failures)} ({100 - success_rate:.1f}%)")
    print(f"Total Time: {total_time:.2f} seconds")
    print(f"Requests/sec: {requests_per_second:.2f}")
    print("\nLatency Statistics (seconds):")
    print(f"  Mean:   {mean_latency*1000:.2f} ms")
    print(f"  Median: {median_latency*1000:.2f} ms")
    print(f"  Min:    {min_latency*1000:.2f} ms")
    print(f"  Max:    {max_latency*1000:.2f} ms")
    print(f"  StdDev: {stdev_latency*1000:.2f} ms")
    print(f"  P95:    {p95_latency*1000:.2f} ms")
    print(f"  P99:    {p99_latency*1000:.2f} ms")
    
    if failures:
        print("\nFailures:")
        error_counts = {}
        for f in failures:
            error = f.get('error', f"HTTP {f.get('status_code', 'unknown')}")
            error_counts[error] = error_counts.get(error, 0) + 1
        for error, count in error_counts.items():
            print(f"  {error}: {count}")
    
    print("=" * 60)
    
    # Save detailed report to file
    report_file = "load_test_report.json"
    report = {
        'timestamp': time.time(),
        'num_requests': num_requests,
        'total_time': total_time,
        'success_rate': success_rate,
        'requests_per_second': requests_per_second,
        'latency_stats': {
            'mean': mean_latency,
            'median': median_latency,
            'min': min_latency,
            'max': max_latency,
            'stdev': stdev_latency,
            'p95': p95_latency,
            'p99': p99_latency
        },
        'success_count': len(successes),
        'failure_count': len(failures),
        'failures': failures[:10]  # Include first 10 failures for debugging
    }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Load test the volatility prediction API')
    parser.add_argument(
        '--url',
        type=str,
        default='http://localhost:8000',
        help='Base URL of the API (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--requests',
        type=int,
        default=100,
        help='Number of requests to send (default: 100)'
    )
    
    args = parser.parse_args()
    
    try:
        report = asyncio.run(run_load_test(args.url, args.requests))
        
        # Exit with error code if success rate is too low
        if report['success_rate'] < 95.0:
            print(f"\n⚠️  Warning: Success rate is {report['success_rate']:.1f}% (below 95%)")
            exit(1)
        else:
            print(f"\n✅ Load test passed: {report['success_rate']:.1f}% success rate")
            exit(0)
    except KeyboardInterrupt:
        print("\n\nLoad test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()

